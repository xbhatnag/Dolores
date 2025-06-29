import puppeteer from "puppeteer";
import { TextToSpeechClient, protos } from '@google-cloud/text-to-speech';
import { promises as fs } from 'fs';
import { exec } from 'node:child_process';
import util from 'node:util'
import Parser from 'rss-parser';
import { decodeHTML } from 'entities';
import { readFile, rm } from "node:fs/promises";
import { GenerativeModel, SchemaType, VertexAI } from '@google-cloud/vertexai';
import { log } from "node:console";

class Queue<T> {
  private data: T[] = [];

  /**
   * Adds an element to the back of the queue.
   * @param element The element to add.
   */
  enqueue(element: T): void {
    this.data.push(element);
  }

  /**
   * Removes and returns the element from the front of the queue.
   * Returns undefined if the queue is empty.
   */
  dequeue(): T | undefined {
    if (this.isEmpty()) {
      return undefined;
    }
    return this.data.shift();
  }

  /**
   * Checks if the queue is empty.
   */
  isEmpty(): boolean {
    return this.data.length === 0;
  }

  /**
   * Returns the number of elements in the queue.
   */
  size(): number {
    return this.data.length;
  }
}

const chirp3_voices = [
        "Puck",
        "Achernar",
        "Laomedeia",
        "Achird",
        "Sadachbia",
        "Kore",
        "Umbriel",
        // "Leda",
        // "Aoede",
        // "Charon",
        // "Fenrir",
        // "Orus",
        // "Zephyr",
        // "Algenib",
        // "Algieba",
        // "Alnilam",
        // "Autonoe",
        // "Callirrhoe",
        // "Despina",
        // "Enceladus",
        // "Erinome",
        // "Gacrux",
        // "Iapetus",
        // "Pulcherrima",
        // "Rasalgethi",
        // "Sadaltager",
        // "Schedar",
        // "Sulafat",
        // "Vindemiatrix",
        // "Zubenelgenubi",
    ]

function getRandomElement<T>(list: T[]): T {
  const randomIndex = Math.floor(Math.random() * list.length);
  return list[randomIndex]!;
}

const execPromise = util.promisify(exec);

function stripHtml(str: string): string {
  str = str.replace(/([^\n])<\/?(h|br|p|ul|ol|li|blockquote|section|table|tr|div)(?:.|\n)*?>([^\n])/gm, '$1\n$3')
  str = str.replace(/<(?:.|\n)*?>/gm, '');
  return str;
}

async function openWebpage(url: string): Promise<void> {
    const browser = await puppeteer.launch({headless: true});
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });
    await page.goto(url);
    const title = await page.title();
    console.log(`Title of the page is: ${title}`);
    await page.screenshot({ path: '/tmp/screenshot.png' });
    await browser.close();
}

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
    intro?: ScriptPiece;
    formal!: ScriptPiece;
    informal?: ScriptPiece;
    voice!: string;
}

async function playOnce(audio_file: string): Promise<void> {
    await execPromise(`ffplay -v 0 -nodisp -autoexit ${audio_file}`);
}

async function playOnceAndDelete(audio_file: string): Promise<void> {
    await playOnce(audio_file);
    await rm(audio_file);
}

async function playScript(script: Script): Promise<void> {
    // Print the script text
    console.log(`VOICE = ${script.voice}`);

    var script_text = '';
    if (script.intro) {
        script_text += script.intro.text;
        script_text += '\n\n';
    }
    script_text += script.formal.text;
    if (script.informal) {
        script_text += '\n\n';
        script_text += script.informal.text;
    }
    script_text += '\n\n';
    console.log(script_text);

    // Play the audio files in order
    if (script.intro) {
        await playOnceAndDelete(script.intro.audio_file);
        await delay(500); // Wait for 500ms before playing formal part
    }

    await playOnceAndDelete(script.formal.audio_file);

    if (script.informal) {
        await delay(700); // Wait for 700ms before playing informal part
        await playOnceAndDelete(script.informal.audio_file);
    }
    
    await delay(1000); // Wait for 1 second before playing the next script
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
        var content = decodeHTML(stripHtml(item.details!)).trim()

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
        var content = decodeHTML(stripHtml(item.details!)).trim()
        article.content = content;
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

function delay(ms: number) {
    return new Promise( resolve => setTimeout(resolve, ms) );
}

/**
 * Interleaves an arbitrary number of arrays (N arrays) with randomness.
 * Elements are picked randomly from any non-empty array until all arrays are exhausted.
 *
 * @template T The type of elements in the arrays.
 * @param {...T[][]} arrays An arbitrary number of arrays to interleave.
 * @returns {T[]} A new array with elements interleaved from all input arrays.
 */
function interleaveArrays<T>(...arrays: T[][]): T[] {
  const result: T[] = [];
  // An array to keep track of the current index for each input array
  const pointers = new Array(arrays.length).fill(0);

  // Loop as long as there's at least one array with remaining elements
  while (true) {
    const availableIndices: number[] = [];

    // Find which arrays still have elements to contribute
    for (let i = 0; i < arrays.length; i++) {
      if (pointers[i] < arrays[i].length) {
        availableIndices.push(i);
      }
    }

    // If no arrays have elements left, break the loop
    if (availableIndices.length === 0) {
      break;
    }

    // Randomly select one of the available arrays
    const randomIndex = Math.floor(Math.random() * availableIndices.length);
    const selectedArrayIndex = availableIndices[randomIndex];

    // Push the element from the selected array to the result
    result.push(arrays[selectedArrayIndex][pointers[selectedArrayIndex]]);

    // Increment the pointer for the array from which an element was taken
    pointers[selectedArrayIndex]++;
  }

  return result;
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

    const the_verge_long_form = await readTheVergeLongForm();
    const the_verge_quick_posts = await readTheVergeQuickPosts();
    const ars_technica = await readArsTechnica();
    const hack_a_day = await readHackADay();

    const articles = interleaveArrays(
        hack_a_day,
        the_verge_quick_posts,
        the_verge_long_form,
        ars_technica
    ).slice(0, 5);

    for (const article of articles) {
        article.print();
    }
    
    for (const [index, article] of articles.entries()) {
        const script = await createScript(tts, speechWriter, article, `script_${index}`);
        scripts.enqueue(script);
    }
}


async function main(): Promise<void> {
    console.log("Welcome to Jockey!");

    const scripts = new Queue<Script>();
    
    // The script writer loop will run in the background
    // and generate scripts while we play them.
    scriptWriterLoop(scripts);

    await playOnce('intro.mp3'); // Play an intro sound
    while (true) {
        if (scripts.isEmpty()) {
            console.log("No scripts available. Waiting for new scripts to be generated...");
            await playOnce('waiting.mp3'); // Play a waiting sound
            continue;
        }
        await delay(700); // Wait for 1 seconds before playing the next script
        await playOnce('transition.mp3'); // Play a transition sound
        const script = scripts.dequeue()!;
        await playScript(script);
    }
}
main()