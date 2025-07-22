'use client';
import { FaExternalLinkAlt } from "react-icons/fa";
import React, { useState, useEffect } from 'react';

interface NewsStory {
  uuid: string,
  conclusion: string,
  summary: string,
  feelings: string,
  url: string
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetch_retry(url: string) {
  while (true) {
    try {
      const response = await fetch(url);
      if (response.status != 200) {
        console.error("Error from /next API", response);
        continue;
      }
      return await response.json();
    } catch (e) {
      console.error("Error from /next API", e);
      await sleep(10000);
    }
  }
}

const App = () => {
  // State to hold the news events, initially an empty array
  const [serious, setSerious] = useState<Array<NewsStory>>([]);
  const [light, setLight] = useState<Array<NewsStory>>([]);
  const [anxiety, setAnxiety] = useState<Array<NewsStory>>([]);
  // State to manage loading status
  const [isLoading, setIsLoading] = useState(true);
  // State to manage potential errors
  const [error, setError] = useState(null);
  const [isRunning, setRunning] = useState(false);
  const [category, setCategory] = useState("Light");
  const [selected, setSelected] = useState("");

  // useEffect hook to perform data fetching when the component mounts
  useEffect(() => {
    const putNews = async (story: NewsStory) => {
      console.log(`${story.conclusion} [${story.feelings}]`);
      if (story.feelings == "Serious") {
        setSerious(prevSerious => [story, ...prevSerious])
      } else if (story.feelings == "Light") {
        setLight(prevLight => [story, ...prevLight])
      } else if (story.feelings == "Anxiety") {
        setAnxiety(prevAnxiety => [story, ...prevAnxiety])
      }
      setIsLoading(false); // Set loading to false
    };

    const getNextNews = async () => {
      if (!isRunning) {
        return;
      }

      try {
        console.log("Fetching next story...");
        const story: NewsStory = await fetch_retry("http://localhost:8080/next");
        console.log(`${story.conclusion} [${story.feelings}]`);

        putNews(story);

        // Try again
        setTimeout(getNextNews, 1000);
      } catch (err) {
        setError(err.message); // Set error message
        setIsLoading(false); // Set loading to false
      }
    };

    const getAllNews = async () => {
      if (!isRunning) {
        return;
      }

      try {
        console.log("Fetching all existing stories...");
        const stories: Array<NewsStory> = await fetch_retry("http://localhost:8080/all");

        // Load all existing stories
        for (const story of stories) {
          putNews(story);
        }

        getNextNews();
      } catch (err) {
        setError(err.message); // Set error message
        setIsLoading(false); // Set loading to false
      }
    };

    if (isRunning) {
      getAllNews();
    }
  }, [isRunning]); // Empty dependency array means this effect runs once after the initial render

  const toggleRunning = () => {
    console.log(`Flipping state to ${!isRunning}`)
    setRunning(!isRunning);
  }

  const tabs = () => {
    var serious_color = "bg-gray-100 hover:bg-gray-200"
    var light_color = "bg-gray-100 hover:bg-gray-200"
    var anxiety_color = "bg-gray-100 hover:bg-gray-200"

    if (category == "Serious") {
      serious_color = "bg-gray-800"
    } else if (category == "Light") {
      light_color = "bg-gray-800"
    } else if (category == "Anxiety") {
      anxiety_color = "bg-gray-800"
    }

    return (
      <div className="flex gap-5">
        <button className={`text-4xl ${serious_color} tracking-tight rounded-full p-2 h-15 w-15`} onClick={() => setCategory("Serious")}>
          😐
        </button>
        <button className={`text-4xl ${light_color} tracking-tight rounded-full p-2 h-15 w-15`} onClick={() => setCategory("Light")}>
          😄
        </button>
        <button className={`text-4xl ${anxiety_color} tracking-tight rounded-full p-2 h-15 w-15`} onClick={() => setCategory("Anxiety")}>
          😥
        </button>
      </div>
    )
  }

  const getFavicon = (url: string) => {
    try {
      const urlObject = new URL(url);
      const favicon = `https://${urlObject.hostname}/favicon.ico`;
      return <img src={favicon} className="h-6" />;
    } catch (error) {
      console.error("Invalid URL:", error);
      return <FaExternalLinkAlt className="text-gray-800" />; // Handle bad URLs
    }
  }

  const storiesList = () => {
    var stories = null
    if (category == "Serious") {
      stories = serious
    } else if (category == "Light") {
      stories = light
    } else if (category == "Anxiety") {
      stories = anxiety
    } else {
      throw `Unexpected category: ${category}`;
    }
    return (
      <div className="flex flex-col gap-5">
        {stories.map((story) => (
          <div key={story.uuid} className="flex flex-col bg-gray-100 rounded-xl p-5" onClick={() => setSelected(story.uuid)}>
            <div className="relative flex text-left flex items-center gap-2 mb-1">
              <div className="text-base sm:text-lg font-semibold text-gray-800 leading-tight grow">
                {story.conclusion}
              </div>
            </div>
            <div className="text-base sm:text-lg text-gray-600 leading-tight">
              {story.summary}
            </div>

            {/* Conditional if selected */}
            {story.uuid == selected &&
              <div className="flex flex-col gap-2">
                <a href={story.url}>{getFavicon(story.url)}</a>
                <input className="bg-white rounded-l text-gray-800 mt-2 p-2" placeholder="Ask a question"></input>
              </div>
            }
          </div>
        ))}
      </div>
    );
  }


  return (
    // Main container with Inter font and minimal background
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Page Title */}
      <header className="bg-gray-70 flex">
        <h1 onClick={toggleRunning} className="text-5xl text-gray-800 tracking-tight grow">
          Dolores
          &nbsp;
          {isRunning && "✅"}
          {!isRunning && "❌"}
        </h1>
        {tabs()}
      </header>

      {/* Conditional rendering based on loading and error states */}
      {isRunning && isLoading && (
        <div className="text-center text-gray-600 text-lg">Loading news events...</div>
      )}
      {error && (
        <div className="text-center text-red-600 text-lg">Error: {error}</div>
      )}

      {!isLoading && !error && (
        <div className="relative mx-auto space-y-12 p-5 max-w-[calc(50%)] mt-5">
          {storiesList()}
        </div>
      )}
    </div>
  );
};

export default App;
