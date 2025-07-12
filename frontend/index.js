"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
window.onload = () => {
    console.log("Page loaded!");
    const script_html = {
        article_window: document.getElementById("article-window"),
        camera_window: document.getElementById("camera-window"),
        qr_code_window: document.getElementById("qr-code-window"),
        loading: document.getElementById("loading"),
        title: document.getElementById("title"),
        description: document.getElementById("description"),
        hero: document.getElementById("hero"),
        qr_code: document.getElementById("qr-code"),
        footer_1: document.getElementById("footer-1"),
        footer_2: document.getElementById("footer-2"),
        narrator: document.getElementById("narrator")
    };
    clock_loop(document.getElementById("clock"));
    // Set the scroller text
    document.getElementById("scroller").textContent = [
        "Jockey is an AI radio that promotes interesting tech articles on the internet. It as an experimental side project, created for fun and not for monetization.",
        "The RSS feeds of each publication are used to generate Jockey's audio summaries. Please support these publications so they can continue to produce great work! ❤️",
        "Generative AI ✨ can make mistakes, so double check it.",
        "Jockey was created by Xyan Bhatnagar (xyan.pro)"
    ].join("\u00A0".repeat(100));
    // Cycle through news articles by pressing the button
    document.getElementById("start-button").onclick = () => {
        play_next("http://localhost:8080/next", script_html);
    };
};
function base64ToArrayBuffer(base64) {
    try {
        const binaryString = window.atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }
    catch (e) {
        throw new Error("Invalid Base64 string provided.");
    }
}
// Declare AudioContext outside to be potentially reused or closed
let audioContext = null;
function playAudioFromBytes(audioData, callback) {
    return __awaiter(this, void 0, void 0, function* () {
        console.log(`Playing audio [filesize:${audioData.byteLength}]`);
        try {
            // Create (or resume) an AudioContext
            if (!audioContext) {
                audioContext = new window.AudioContext();
            }
            else if (audioContext.state === 'suspended') {
                yield audioContext.resume();
            }
            // Decode the audio data from the ArrayBuffer
            // This is the crucial step for playing raw bytes.
            const audioBuffer = yield audioContext.decodeAudioData(audioData);
            // Create a buffer source node
            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            // Connect to the audio context's destination (speakers)
            source.connect(audioContext.destination);
            // Start playing the audio
            source.start(0); // Play immediately
            // Optional: Update status when audio finishes playing
            source.onended = callback;
        }
        catch (error) {
            console.error('Error playing audio:', error);
            // Attempt to close context on error
            audioContext === null || audioContext === void 0 ? void 0 : audioContext.close();
            audioContext = null;
        }
    });
}
function clock_loop(clock_html) {
    return __awaiter(this, void 0, void 0, function* () {
        while (true) {
            clock_html.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const now = new Date();
            const seconds = now.getSeconds();
            const milliseconds = now.getMilliseconds();
            // Calculate milliseconds until the next full minute
            // (60 seconds - current seconds) * 1000 ms/s - current milliseconds
            const msUntilNextMinute = (60 - seconds) * 1000 - milliseconds;
            // Ensure it's at least 0 (e.g., if called exactly on the minute)
            const delay = Math.max(0, msUntilNextMinute);
            yield new Promise(resolve => setTimeout(resolve, delay));
        }
    });
}
function narrator_loop(narrator_html, narrator, should_abort) {
    return __awaiter(this, void 0, void 0, function* () {
        while (true) {
            for (let i = 1; i <= 4; i++) {
                // Exit if we're not playing this script anymore.
                if (should_abort.aborted) {
                    return;
                }
                // Change to the next picture
                narrator_html.src = `narrators/${narrator}_${i}.png`;
                // Wait for 10 seconds before switching it again.
                yield new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
    });
}
function play_next(url, script_html) {
    return __awaiter(this, void 0, void 0, function* () {
        console.log("Retrieving next script...");
        // Show the progress bar
        script_html.loading.style.display = "block";
        // Wait for 5 seconds before starting with the next article.
        yield new Promise(resolve => setTimeout(resolve, 10000));
        // Get the next script
        const response = yield fetch(url);
        const script = yield response.json();
        console.log(script.title);
        // Hide the progress bar
        script_html.loading.style.display = "none";
        // Set the hero image
        script_html.hero.src = `data:image/png;base64,${script.hero}`;
        // Set the title
        script_html.title.textContent = script.title;
        // Set the Audio Text and adjust the height
        script_html.description.textContent = script.description;
        script_html.description.style.height = 'auto';
        script_html.description.style.height = script_html.description.scrollHeight + 'px';
        // Set the QR Code
        script_html.qr_code.src = `data:image/png;base64,${script.qr_code}`;
        // Set the footers
        script_html.footer_1.textContent = script.footer_1;
        script_html.footer_2.textContent = script.footer_2;
        // Start the loop of narrator pictures
        const controller = new AbortController();
        narrator_loop(script_html.narrator, script.narrator, controller.signal);
        // Play the audio and trigger the abort signal when done
        playAudioFromBytes(base64ToArrayBuffer(script.audio), () => {
            // Stop the old narrator loop
            controller.abort();
            // Start a new playback
            play_next(url, script_html);
        });
    });
}
