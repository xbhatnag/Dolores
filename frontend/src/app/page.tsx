'use client';
import React, { useState, useEffect } from 'react';
import { Tree, TreeItem, TreeItemContent, Selection, } from 'react-aria-components';

interface NewsStory {
  uuid: string,
  conclusion: string,
  summary: string,
  feelings: string,
  url: string
}

interface TreeNode {
  subcategories: Map<string, TreeNode>,
  stories: Array<NewsStory>
}

function convertToTreeNode(jsonObject: any): TreeNode {
  const node: TreeNode = {
    subcategories: new Map<string, TreeNode>(),
    stories: jsonObject.stories || [], // Ensure stories is an array
  };

  // Convert subcategories object to Map recursively
  if (jsonObject.subcategories && typeof jsonObject.subcategories === 'object') {
    for (const key in jsonObject.subcategories) {
      if (Object.prototype.hasOwnProperty.call(jsonObject.subcategories, key)) {
        node.subcategories.set(key, convertToTreeNode(jsonObject.subcategories[key]));
      }
    }
  }

  return node;
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
  const [root, setRoot] = useState<TreeNode | null>(null);
  // State to manage potential errors
  const [error, setError] = useState(null);
  const [isRunning, setRunning] = useState(false);
  const [category, setCategory] = useState("Light");
  let [selectedKeys, setSelectedKeys] =
    React.useState<Selection>(new Set());
  const [selectedStory, setSelectedStory] = useState("");

  // useEffect hook to perform data fetching when the component mounts
  useEffect(() => {
    const url = "http://10.0.0.110:7000";

    const waitForTreeUpdate = async () => {
      if (!isRunning) {
        return;
      }

      try {
        console.log("Waiting for tree updates...");
        const json_obj = await fetch_retry(url + "/next");
        const new_root = convertToTreeNode(json_obj)
        console.log(new_root);
        setRoot(new_root);
        setTimeout(waitForTreeUpdate, 1000);
      } catch (err: any) {
        setError(err.message); // Set error message
      }
    };

    const getTree = async () => {
      if (!isRunning) {
        return;
      }

      try {
        console.log("Fetching tree...");
        const json_obj = await fetch_retry(url + "/tree");
        const new_root = convertToTreeNode(json_obj)
        console.log(new_root);
        setRoot(new_root);
        waitForTreeUpdate();
      } catch (err: any) {
        setError(err.message); // Set error message
      }
    };

    if (isRunning) {
      getTree();
    }
  }, [isRunning]);

  const toggleRunning = () => {
    console.log(`Flipping state to ${!isRunning}`)
    setRunning(!isRunning);
  }

  const getFavicon = (url: string) => {
    try {
      const urlObject = new URL(url);
      const favicon = `https://${urlObject.hostname}/favicon.ico`;
      return <img src={favicon} className="h-6" />;
    } catch (error) {
      console.error("Invalid URL:", error);
      return <div></div>; // Handle bad URLs
    }
  }

  const collectAllStories = (node: TreeNode) => {
    var stories = node.stories
    for (const [_, category] of node.subcategories) {
      stories.push(...collectAllStories(category));
    }
    return stories
  }

  const storiesUi = (node: TreeNode) => {
    const stories = collectAllStories(node)

    return (
      <div className="flex flex-col gap-5">
        {stories.map((story) => (
          <div key={story.uuid} className="flex flex-col bg-gray-100 rounded-xl p-5" onClick={() => setSelectedStory(story.uuid)}>
            <div className="relative flex text-left flex items-center gap-2 mb-1">
              <div className="text-base sm:text-lg font-semibold text-gray-800 leading-tight grow">
                {story.conclusion}
              </div>
            </div>
            <div className="text-base sm:text-lg text-gray-600 leading-tight">
              {story.summary}
            </div>

            {/* Conditional if selected */}
            {story.uuid == selectedStory &&
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

  const createTreeItem = (name: string, node: TreeNode) => {
    return (<TreeItem textValue={name} className="mt-1">
      <TreeItemContent>
        <div className="ps-[calc(calc(var(--tree-item-level)_-_1)_*_calc(var(--spacing)_*_6))]">
          {"> " + name}
        </div>
      </TreeItemContent>
      {
        Array.from(node.subcategories).map(([key, value]) => (
          createTreeItem(key, value) 
        ))
      }
      {
        node.stories.map((s) => (
          <TreeItem textValue={s.conclusion} className="mt-1">
            <TreeItemContent>
              <div className="flex gap-2 ps-[calc(calc(var(--tree-item-level)_-_1)_*_calc(var(--spacing)_*_6))]">
                <a href={s.url} target="_blank">{getFavicon(s.url)}</a>
                {s.conclusion}
              </div>
            </TreeItemContent>
          </TreeItem>
        ))
      }
    </TreeItem>)
  }

  const createTree = (node: TreeNode) => {
    return (<Tree className="text-gray-600 text-xl">
      {
        Array.from(node.subcategories).map(([key, value]) => (
          createTreeItem(key, value) 
        ))
      }
    </Tree>)
  }

  return (
    // Main container with Inter font and minimal background
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Page Title */}
      <header className="bg-gray-70 flex gap-5 items-center">
        <h1 className="text-5xl text-gray-800 tracking-tight">
          Dolores
        </h1>
        <input className="grow text-gray-800 text-4xl bg-gray-100 rounded-full p-5" placeholder='Classifier'></input>
        <div onClick={toggleRunning} className='text-4xl'>
          {isRunning && "✅"}
          {!isRunning && "❌"}
        </div>
      </header>

      {/* Conditional rendering based on loading and error states */}
      {isRunning && root == null && (
        <div className="text-center text-gray-600 text-lg">Loading news events...</div>
      )}
      {error && (
        <div className="text-center text-red-600 text-lg">Error: {error}</div>
      )}

      {root != null && !error && (
        <div className='p-5 mt-5 w-full h-full flex'>
          <div className="h-full w-full">
            {createTree(root)}
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
