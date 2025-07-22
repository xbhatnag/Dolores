
import React from 'react';

// interface NewsStory {
//     title: string,
//     category: string,
//     url: string,
//     text: string
// }

// // window.onload = () => {
// //     console.log("Page loaded!");
// //     const data_html = document.getElementById("data")!;
// //     story_loop("http://localhost:8080/next", data_html);
// // }

// function base64ToArrayBuffer(base64: string): ArrayBuffer {
//     try {
//         const binaryString = window.atob(base64);
//         const len = binaryString.length;
//         const bytes = new Uint8Array(len);
//         for (let i = 0; i < len; i++) {
//             bytes[i] = binaryString.charCodeAt(i);
//         }
//         return bytes.buffer;
//     } catch (e: any) {
//         throw new Error("Invalid Base64 string provided.");
//     }
// }

// // Declare AudioContext outside to be potentially reused or closed
// let audioContext: AudioContext | null = null;

// async function playAudioFromBytes(audioData: ArrayBuffer, callback: () => void): Promise<void> {
//     console.log(`Playing audio [filesize:${audioData.byteLength}]`);

//     try {
//         // Create (or resume) an AudioContext
//         if (!audioContext) {
//             audioContext = new window.AudioContext();
//         } else if (audioContext.state === 'suspended') {
//             await audioContext.resume();
//         }

//         // Decode the audio data from the ArrayBuffer
//         // This is the crucial step for playing raw bytes.
//         const audioBuffer: AudioBuffer = await audioContext.decodeAudioData(audioData);

//         // Create a buffer source node
//         const source: AudioBufferSourceNode = audioContext.createBufferSource();
//         source.buffer = audioBuffer;

//         // Connect to the audio context's destination (speakers)
//         source.connect(audioContext.destination);

//         // Start playing the audio
//         source.start(0); // Play immediately

//         // Optional: Update status when audio finishes playing
//         source.onended = callback;

//     } catch (error: any) {
//         console.error('Error playing audio:', error);
//         // Attempt to close context on error
//         audioContext?.close();
//         audioContext = null;
//     }
// }

// function sleep(ms: number): Promise<void> {
//     return new Promise(resolve => setTimeout(resolve, ms));
// }

// async function get_next_story(url: string): Promise<NewsStory> {
//     while (true) {
//         try {
//             const response = await fetch(url);
//             if (response.status != 200) {
//                 console.error("Error from /next API", response);
//                 continue;
//             }
//             return await response.json();
//         } catch (e) {
//             console.error("Error from /next API", e);
//             await sleep(10000);
//         }
//     }
// }

// async function story_loop(url: string, data_html: HTMLElement) {
//     while (true) {
//         console.log("Retrieving next script...")

//         const script = await get_next_story(url);

//         console.log(script);

//         data_html.textContent = script.title + "\n" + data_html.textContent;

//         await sleep(100);
//     }
// }

// // Helper function to calculate relative time
// const getRelativeTime = (timestamp) => {
//   const now = new Date();
//   const seconds = Math.floor((now - new Date(timestamp)) / 1000);

//   let interval = seconds / 31536000; // years
//   if (interval > 1) return Math.floor(interval) + " year" + (Math.floor(interval) === 1 ? "" : "s") + " ago";
//   interval = seconds / 2592000; // months
//   if (interval > 1) return Math.floor(interval) + " month" + (Math.floor(interval) === 1 ? "" : "s") + " ago";
//   interval = seconds / 86400; // days
//   if (interval > 1) return Math.floor(interval) + " day" + (Math.floor(interval) === 1 ? "" : "s") + " ago";
//   interval = seconds / 3600; // hours
//   if (interval > 1) return Math.floor(interval) + " hour" + (Math.floor(interval) === 1 ? "" : "s") + " ago";
//   interval = seconds / 60; // minutes
//   if (interval > 1) return Math.floor(interval) + " minute" + (Math.floor(interval) === 1 ? "" : "s") + " ago";
//   return Math.floor(seconds) + " second" + (Math.floor(seconds) === 1 ? "" : "s") + " ago";
// };

// const App = () => {
//   // Mock news event data
//   const newsEvents = [
//     { id: 1, title: "Breaking News: Major Tech Acquisition Announced", timestamp: new Date(Date.now() - 1000 * 60 * 30) }, // 30 mins ago
//     { id: 2, title: "Local Elections Conclude with Surprising Results", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2) }, // 2 hours ago
//     { id: 3, title: "New Study Reveals Climate Change Impact", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24) }, // 1 day ago
//     { id: 4, title: "Sports Championship Decided in Thrilling Match", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3) }, // 3 days ago
//     { id: 5, title: "Global Summit Addresses Economic Challenges", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7) }, // 1 week ago
//     { id: 6, title: "Historic Space Mission Successfully Launched", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30) }, // 1 month ago
//     { id: 7, title: "Art Exhibition Opens to Critical Acclaim", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 60) }, // 2 months ago
//     { id: 8, title: "Medical Breakthrough Offers New Hope", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 120) }, // 4 months ago
//     { id: 9, title: "International Trade Deal Finalized", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 180) }, // 6 months ago
//     { id: 10, title: "Ancient Artifact Discovered in Desert", timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 365) }, // 1 year ago
//   ];

//   // Sort events in reverse chronological order (newest first)
//   const sortedEvents = [...newsEvents].sort((a, b) => b.timestamp - a.timestamp);

//   return (
//     // Main container with Inter font and minimal background
//     <div className="min-h-screen bg-gray-50 p-4 sm:p-8 font-inter">
//       {/* Page Title */}
//       <h1 className="text-3xl sm:text-4xl font-extrabold text-center mb-8 sm:mb-12 text-gray-800 tracking-tight">
//         News Timeline
//       </h1>

//       {/* Timeline Container */}
//       <div className="relative max-w-3xl mx-auto py-4">
//         {/* Vertical Timeline Line */}
//         <div className="absolute left-1/2 transform -translate-x-1/2 h-full w-0.5 bg-gray-300 rounded-full"></div>

//         {/* Individual News Events */}
//         <div className="space-y-12">
//           {sortedEvents.map((event) => (
//             <div key={event.id} className="relative flex items-center justify-center">
//               {/* Left side: Relative Time */}
//               <div className="w-1/2 pr-6 sm:pr-8 text-right">
//                 <span className="text-xs sm:text-sm text-gray-600 font-medium">
//                   {getRelativeTime(event.timestamp)}
//                 </span>
//               </div>
//               {/* Dot on the timeline */}
//               <div className="relative w-3 h-3 bg-blue-500 rounded-full flex-shrink-0 z-10 border-2 border-white transform -translate-x-1/2"></div>
//               {/* Right side: News Title */}
//               <div className="w-1/2 pl-6 sm:pl-8 text-left">
//                 <h3 className="text-base sm:text-lg font-semibold text-gray-800 leading-tight">
//                   {event.title}
//                 </h3>
//               </div>
//             </div>
//           ))}
//         </div>
//       </div>
//     </div>
//   );
// };

// export default App;

function MyButton() {
  return (
    <button>I'm a button</button>
  );
}

export default function MyApp() {
  return (
    <div>
      <h1>Welcome to my app</h1>
      <MyButton />
    </div>
  );
}