import puppeteer from "puppeteer";
import { TextToSpeechClient, protos } from '@google-cloud/text-to-speech';
import { promises as fs } from 'fs';
import { exec } from 'node:child_process';
import util from 'node:util'

const execPromise = util.promisify(exec);

async function playAudio(data : string | Uint8Array): Promise<void> {
    await fs.writeFile('/dev/shm/audio.mp3', data, 'binary');
    const {stdout, stderr} = await execPromise('ffplay -v 0 -nodisp -autoexit /dev/shm/audio.mp3');
}

async function speak(tts: TextToSpeechClient, text: string) {
    console.log(`Converting text to speech: ${text}`);

    // Construct the TTS request
    const request: protos.google.cloud.texttospeech.v1.ISynthesizeSpeechRequest = {
        input: {text: text},
        // Select the language and SSML voice gender (optional)
        voice: {name: 'en-US-Studio-O', languageCode: 'en-US', ssmlGender: 'FEMALE'},
        // select the type of audio encoding
        audioConfig: {audioEncoding: 'MP3'},
    };

    // Performs the text-to-speech request
    const [response] = await tts.synthesizeSpeech(request);

    if (!response.audioContent) {
        throw new Error('No audio content received');
    }

    playAudio(response.audioContent);
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

async function main(): Promise<void> {
    console.log("Welcome to Jockey!");

    const tts = new TextToSpeechClient({projectId: 'dolores-cb057'});
    const text = "Welcome to Jockey!";
    
    await speak(tts, text);
}

main()