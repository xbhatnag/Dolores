import puppeteer from "puppeteer";
import { TextToSpeechClient, protos } from '@google-cloud/text-to-speech';
import { promises as fs } from 'fs';
import { exec } from 'node:child_process';
import util from 'node:util'
import Parser from 'rss-parser';
import { decodeHTML } from 'entities';
import { readFile, rm } from "node:fs/promises";
import { GenerativeModel, VertexAI } from '@google-cloud/vertexai';

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
}

class Script {
    article!: Article;
    formal_text!: string;
    informal_text!: string;
    formal_audio_file!: string;
    informal_audio_file!: string;
}

async function playAndDeleteAudio(audio_file: string): Promise<void> {
    await execPromise(`ffplay -v 0 -nodisp -autoexit ${audio_file}`);
    await rm(audio_file);
}

async function playScript(script: Script): Promise<void> {
    console.log('-----------------------------------');
    console.log(`📰 ${script.article.title}`);
    console.log(`✍️ ${script.article.author} @ ${script.article.source}`);
    console.log(`🌐 ${script.article.url}`)

    console.log('-----------------------------------');
    console.log(script.formal_text);
    console.log('');
    console.log(script.informal_text);

    await playAndDeleteAudio(script.formal_audio_file);
    await delay(700); // Wait for 700ms before playing informal part

    await playAndDeleteAudio(script.informal_audio_file);
    await delay(1000); // Wait for 1 second before playing the next script
}

async function getAudio(tts: TextToSpeechClient, text: string, filename: string): Promise<string> {
    // Construct the TTS request
    const request: protos.google.cloud.texttospeech.v1.ISynthesizeSpeechRequest = {
        input: {text: text},
        // Select the language and SSML voice gender (optional)
        voice: {name: 'en-US-Chirp3-HD-Achernar', languageCode: 'en-US'},
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

async function readTheVerge(): Promise<Article[]> {
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
        article.content = summary;
        article.url = item.link!;
        
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

        article.url = item.link!.trim();
        
        return article;
    });
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

    const parts = text.split('...\n');
    script.formal_text = parts[0].trim();
    script.informal_text = parts[1].trim(); 

    const formal_file_name = `${filename}_formal`;
    const informal_file_name = `${filename}_informal`;

    script.formal_audio_file = await getAudio(tts, script.formal_text, formal_file_name);
    script.informal_audio_file = await getAudio(tts, script.informal_text, informal_file_name);

    return script;
}

function delay(ms: number) {
    return new Promise( resolve => setTimeout(resolve, ms) );
}

/**
 * Interleaves two arrays with some randomness, taking elements alternately
 * or randomly from each. If one array is longer than the other, the remaining
 * elements of the longer array are appended to the result.
 *
 * @template T The type of elements in the arrays.
 * @param {T[]} arr1 The first array.
 * @param {T[]} arr2 The second array.
 * @returns {T[]} A new array with elements interleaved from arr1 and arr2.
 */
function interleaveArrays<T>(arr1: T[], arr2: T[]): T[] {
  const result: T[] = [];
  let i = 0; // Pointer for arr1
  let j = 0; // Pointer for arr2

  while (i < arr1.length || j < arr2.length) {
    const hasMoreArr1 = i < arr1.length;
    const hasMoreArr2 = j < arr2.length;

    // If both arrays have elements, randomly decide which one to pick from
    if (hasMoreArr1 && hasMoreArr2) {
      if (Math.random() < 0.5) { // 50% chance to pick from arr1
        result.push(arr1[i]);
        i++;
      } else { // 50% chance to pick from arr2
        result.push(arr2[j]);
        j++;
      }
    } else if (hasMoreArr1) {
      // If only arr1 has elements left, push from arr1
      result.push(arr1[i]);
      i++;
    } else if (hasMoreArr2) {
      // If only arr2 has elements left, push from arr2
      result.push(arr2[j]);
      j++;
    }
  }

  return result;
}

async function main(): Promise<void> {
    console.log("Welcome to Jockey!");

    const systemPrompt = await readFile('./system_prompt.md', 'utf8');
    console.log("---------- System Prompt -----------");
    console.log(systemPrompt);
    console.log("------------------------------------");

    const tts = new TextToSpeechClient({projectId: 'dolores-cb057'});
    const vertexAI = new VertexAI({project: 'dolores-cb057', location: 'us-west1'});
    
    const speechWriter = vertexAI.getGenerativeModel({
        model: 'gemini-2.5-pro',
        systemInstruction: {
            role: 'system',
            parts: [{"text": systemPrompt}]
        },
    });

    const the_verge = await readTheVerge();
    the_verge.reverse(); // Reverse the order to get the oldest articles first

    const ars_technica = await readArsTechnica();
    ars_technica.reverse(); // Reverse the order to get the oldest articles first

    const articles = interleaveArrays(the_verge, ars_technica);

    const script_promises: Promise<Script>[] = [];
    
    for (const [index, article] of articles.entries()) {
        script_promises.push(createScript(tts, speechWriter, article, `script_${index}`));
    }

    for (const promise of script_promises) {
        const script = await promise;
        await playScript(script);
        await delay(1000); // Wait for 1 second before playing the next script
    }
}

main()