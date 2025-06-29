import { TextToSpeechClient, protos } from '@google-cloud/text-to-speech';
import { promises as fs } from 'fs';
import Parser from 'rss-parser';
import { readFile, rm } from "node:fs/promises";
import { GenerativeModel, SchemaType, VertexAI } from '@google-cloud/vertexai';
import { Queue } from './queue.js';
import { execPromise, interleaveArrays, getRandomElement, stripHtml, delay } from './utils.js';
import { exec, ChildProcess } from 'node:child_process';

const chirp3_voices = [
    "Puck",
    "Achernar",
    "Laomedeia",
    "Achird",
    "Sadachbia",
]


class Article {
    source!: string;
    title!: string;
    author!: string;
    content!: string;
    url!: string;
    pubDate!: Date;

    // Print the article information
    print() {
        console.log(
            `-----------------------------------\n📰 ${this.title}\n✍️ ${this.author} @ ${this.source}\n🌐 ${this.url}\n📅 ${this.pubDate.toLocaleDateString()}\n-----------------------------------`
        )
    }
}

class ScriptPiece {
    text!: string;
    audio_file!: string;
}

class Script {
    // The article that this script is based on
    article!: Article;

    // The intro text and audio file, if any
    intro?: ScriptPiece;

    // The formal voiceover text and audio file
    formal!: ScriptPiece;

    // The informal opinion piece text and audio file, if any
    informal?: ScriptPiece;

    // The voice used for this script
    voice!: string;

    async play(): Promise<void> {
        // Print the script text
        var script_text = `-----------------------------------\n🗣️ Narrated by ${this.voice}\n\n`;
        if (this.intro) {
            script_text += this.intro.text;
            script_text += '\n\n';
        }
        script_text += this.formal.text;
        if (this.informal) {
            script_text += '\n\n';
            script_text += this.informal.text;
        }
        script_text += '\n-----------------------------------\n';
        console.log(script_text);

        // Play the audio files in order
        if (this.intro) {
            await playOnceAndDelete(this.intro.audio_file);
            await delay(500); // Wait for 500ms before playing formal part
        }

        await playOnceAndDelete(this.formal.audio_file);

        if (this.informal) {
            await delay(700); // Wait for 700ms before playing informal part
            await playOnceAndDelete(this.informal.audio_file);
        }
        
        await delay(1000); // Wait for 1 second before playing the next script
    }
}

async function playOnce(audio_file: string): Promise<void> {
    await execPromise(`ffplay -v 0 -nodisp -autoexit ${audio_file}`);
}

function playLoop(audio_file: string): ChildProcess {
    return exec(`ffplay -v 0 -nodisp -loop 0 ${audio_file}`);
}

async function playOnceAndDelete(audio_file: string): Promise<void> {
    await playOnce(audio_file);
    await rm(audio_file);
}

async function getAudio(tts: TextToSpeechClient, text: string, filename: string, voice: string): Promise<string> {
    // Construct the TTS request
    const request: protos.google.cloud.texttospeech.v1.ISynthesizeSpeechRequest = {
        input: {text: text},
        // Select the language and SSML voice gender (optional)
        voice: {name: `en-US-Chirp3-HD-${voice}`, languageCode: 'en-US'},
        // select the type of audio encoding
        audioConfig: {audioEncoding: 'MP3'},
    };

    // Performs the text-to-speech request
    const [response] = await tts.synthesizeSpeech(request);

    if (!response.audioContent) {
        throw new Error('No audio content received');
    }

    const path = `/dev/shm/${filename}.mp3`;
    await fs.writeFile(path, response.audioContent, 'binary');

    return path;
}

async function readTheVergeLongForm(): Promise<Article[]> {
    const parser = new Parser({
        customFields: {
            item: ['summary', 'author'],
        },
    });
    const feed = await parser.parseURL('https://www.theverge.com/rss/index.xml');
    return feed.items.map(item => {
        const article = new Article();
        article.source = 'The Verge';
        article.title = item.title!;
        article.author = item.author!;
        let summary = item.summary!;
        if (summary.endsWith('[&#8230;]')) {
            summary = summary.slice(0, -9).trim();
            summary += '[…]'; // Add ellipsis to indicate truncation
        }
        article.pubDate = new Date(item.pubDate!);
        article.content = summary;
        article.url = item.link!;
        
        return article;
    });
}

async function readTheVergeQuickPosts(): Promise<Article[]> {
    const parser = new Parser({
        customFields: {
            item: ['summary', 'author'],
        },
    });
    const feed = await parser.parseURL('https://www.theverge.com/rss/quickposts');
    return feed.items.map(item => {
        const article = new Article();
        article.source = 'The Verge';
        article.title = item.title!;
        article.author = item.author!;
        article.content = item.summary!;
        article.url = item.link!;
        article.pubDate = new Date(item.pubDate!);
        
        return article;
    });
}

async function readArsTechnica(): Promise<Article[]> {
    const parser = new Parser({
        customFields: {
            item: [['content:encoded', 'details']],
        },
    });
    const feed = await parser.parseURL('https://feeds.arstechnica.com/arstechnica/index');
    return feed.items.map(item => {
        const article = new Article();
        article.source = 'Ars Technica';
        article.title = item.title!.trim();
        article.author = item.creator!.trim();
        var content = stripHtml(item.details!)

        if (content.endsWith('Read full article\nComments')) {
            content = content.slice(0, -27).trim(); // Remove the trailing '
        }
        article.content = content;
        article.pubDate = new Date(item.pubDate!);
        article.url = item.link!.trim();
        
        return article;
    });
}

async function readHackADay(): Promise<Article[]> {
    const parser = new Parser({
        customFields: {
            item: [['content:encoded', 'details']],
        },
    });
    const feed = await parser.parseURL('https://hackaday.com/blog/feed/');
    return feed.items.map(item => {
        const article = new Article();
        article.source = 'Hack A Day';
        article.title = item.title!.trim();
        article.author = item.creator!.trim();
        article.content = stripHtml(item.details!);
        article.pubDate = new Date(item.pubDate!);
        article.url = item.link!.trim();
        
        return article;
    });
}

function flipCoin(odds: number = 0.5): boolean {
    return Math.random() < odds;
}

async function createScript(
    tts: TextToSpeechClient,
    speechWriter: GenerativeModel,
    article: Article,
    filename: string
): Promise<Script> {
    const script = new Script();
    script.article = article;

    const prompt = `Move onto this article:\n\n
    News Organization: ${article.source}\n
    Title: ${article.title}\n
    Author: ${article.author}\n
    Content: ${article.content}`;
    
    const result = await speechWriter.generateContent({
        contents: [{
            role: 'user',
            parts: [{text: prompt}]
        }]
    });

    const text = result.response.candidates![0].content.parts[0].text!;
    const object = JSON.parse(text); // Validate the JSON structure

    // Pick a random Chirp3 voice
    script.voice = getRandomElement(chirp3_voices);

    if (flipCoin()) {
        // 50-50 odds of including an intro
        script.intro = new ScriptPiece();
        script.intro.text = object.intro.trim();
        const intro_file_name = `${filename}_intro`;
        script.intro.audio_file = await getAudio(tts, script.intro.text, intro_file_name, script.voice);
    }

    script.formal = new ScriptPiece();
    script.formal.text = object.formal.trim();
    const formal_file_name = `${filename}_formal`;
    script.formal.audio_file = await getAudio(tts, script.formal.text, formal_file_name, script.voice);

    if (flipCoin(0.5)) {
        // 50-50 odds of including an opinion piece
        script.informal = new ScriptPiece();
        script.informal.text = object.informal.trim(); 
        const informal_file_name = `${filename}_informal`;
        script.informal.audio_file = await getAudio(tts, script.informal.text, informal_file_name, script.voice);
    }

    return script;
}

async function scriptWriterLoop(scripts: Queue<Script>): Promise<void> {
    const systemPrompt = await readFile('./system_prompt.md', 'utf8');
    const tts = new TextToSpeechClient({projectId: 'dolores-cb057'});
    const vertexAI = new VertexAI({project: 'dolores-cb057', location: 'us-west1'});
    
    const speechWriter = vertexAI.getGenerativeModel({
        model: 'gemini-2.5-pro',
        generationConfig: {
            responseMimeType: 'application/json',
            responseSchema: {
                type: SchemaType.OBJECT,
                properties: {
                    intro: {
                        type: SchemaType.STRING,
                        description: 'The one-line introduction to the article',
                        nullable: false,
                        example: 'Here\'s an interesting article from The Verge about AI.'
                    },
                    formal: {
                        type: SchemaType.STRING,
                        description: 'The formal summary of the article',
                        nullable: false,
                        example: 'The Verge reports that AI is revolutionizing the tech industry with new advancements in natural language processing and computer vision.'
                    },
                    informal: {
                        type: SchemaType.STRING,
                        description: 'The informal opinion piece of the news anchor',
                        nullable: false,
                        example: 'Honestly, I think AI is both exciting and a bit scary. It\'s amazing what it can do, but we need to be careful about how we use it.'
                    }
                },
                required: ['intro', 'formal', 'informal'],
                nullable: false,
            }
        },
        systemInstruction: {
            role: 'system',
            parts: [{"text": systemPrompt}]
        },
    });

    // Read the entire feeds
    const the_verge_long_form = await readTheVergeLongForm();
    const the_verge_quick_posts = await readTheVergeQuickPosts();
    const ars_technica = await readArsTechnica();
    const hack_a_day = await readHackADay();

    const articles = interleaveArrays(
        hack_a_day,
        the_verge_quick_posts,
        the_verge_long_form,
        ars_technica
    );

    for (const article of articles) {
        article.print();
    }
    
    for (const [index, article] of articles.entries()) {
        const script = await createScript(tts, speechWriter, article, `script_${index}`);
        scripts.enqueue(script);
    }

    // Now start listening for changes to any of the feeds
}

async function newsAnchorLoop(scripts: Queue<Script>): Promise<void> {
    // The child process that plays the infinite looping waiting sound
    // while we wait for scripts to be generated.
    var waitingAudioProcess: ChildProcess | undefined;

    while (true) {
        while (scripts.isEmpty()) {
            await delay(5000); // Wait for 5 seconds before checking again

            // Start the waiting sound if it's not already playing
            if (waitingAudioProcess === undefined) {
                waitingAudioProcess = playLoop('waiting.mp3');
            }
        }

        // We have a script to play now.
        if (waitingAudioProcess) {
            // If we were playing a waiting sound, kill it
            waitingAudioProcess.kill();
            waitingAudioProcess = undefined;

            // Wait for a short time to let the sound stop
            await delay(500);

            // Play the intro sound because this is the first script in a while
            await playOnce('intro.mp3');
        } else {
            // Transitioning from an old script to a new one
            await delay(700); // Wait before playing the next script
            await playOnce('transition.mp3'); // Play a transition sound
        }

        // Play the next script
        const script = scripts.dequeue()!;
        await script.play();
    }
}


async function main(): Promise<void> {
    console.log("Welcome to Jockey!");

    // Create a queue to hold the scripts
    // This will allow us to play scripts in the order they are generated.
    const scripts = new Queue<Script>();
    
    // The script writer loop will run in the background
    // and generate scripts while we play them.
    scriptWriterLoop(scripts);

    // The news anchor loop will run in the foreground
    // and play the scripts as they are generated.
    await newsAnchorLoop(scripts);
}

// Start the main function
main()