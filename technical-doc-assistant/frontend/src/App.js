import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

function App() {
  const [userInput, setUserInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [repoId, setRepoId] = useState('');
  const chatEndRef = useRef(null);
  const pollingIntervalRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const addMessageToHistory = (text, sender) => {
    setChatHistory(prevHistory => [...prevHistory, { text, sender }]);
  };

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };

  // Cleanup effect to stop polling if the component unmounts
  useEffect(() => {
    return () => stopPolling();
  }, []);

  const pollIndexingStatus = (repoId) => {
    stopPolling(); // Stop any previous polling
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/index-status/${repoId}`);
        if (response.data.status === 'complete') {
          stopPolling();
          addMessageToHistory(`Great, the repository '${repoId}' is ready. What would you like to know about it?`, 'bot');
          setIsLoading(false);
        }
      } catch (error) {
        stopPolling();
        addMessageToHistory(`An error occurred while checking status. Please try again.`, 'bot-error');
        setIsLoading(false);
      }
    }, 3000); // Poll every 3 seconds
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!userInput.trim() || isLoading) return;

    const currentInput = userInput;
    addMessageToHistory(currentInput, 'user');
    setUserInput('');
    setIsLoading(true);

    try {
      if (currentInput.toLowerCase().includes('github.com')) {
        addMessageToHistory("Got it. Indexing that repository. This can take up to a minute...", 'bot-status');
        const response = await axios.post(`${API_URL}/index-repo`, { repo_url: currentInput });
        const currentRepoId = response.data.repo_id;
        setRepoId(currentRepoId);
        
        if (response.data.status === 'pending') {
          pollIndexingStatus(currentRepoId);
        } else {
          addMessageToHistory(`Repository '${currentRepoId}' was already indexed. What would you like to know?`, 'bot');
          setIsLoading(false);
        }
      } else {
        if (!repoId) {
          addMessageToHistory("Please provide a GitHub repository URL first.", 'bot-error');
          setIsLoading(false);
          return;
        }
        addMessageToHistory("Thinking...", 'bot-status');
        const response = await axios.post(`${API_URL}/query`, { repo_id: repoId, question: currentInput });
        setChatHistory(prev => {
          const newHistory = [...prev];
          newHistory[newHistory.length - 1] = { text: response.data.answer, sender: 'bot' };
          return newHistory;
        });
        setIsLoading(false);
      }
    } catch (error) {
      const errorMessage = `An error occurred: ${error.response ? error.response.data.detail : error.message}`;
      addMessageToHistory(errorMessage, 'bot-error');
      setIsLoading(false);
    }
  };
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
    }
  };

  useEffect(() => {
      addMessageToHistory("Welcome! Please start by pasting a public GitHub repository URL.", 'bot');
      // The line below is for the final, local version of index.js.
      // If you are using StrictMode in index.js, this welcome message may appear twice.
  }, []);

  return (
    <div className="App">
      <div className="chat-window">
        {chatHistory.map((message, index) => (
          <div key={index} className={`message ${message.sender}`}>
            {message.sender === 'bot' ? <ReactMarkdown>{message.text}</ReactMarkdown> : <pre>{message.text}</pre>}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder={isLoading ? "Processing..." : "Enter a GitHub URL or ask a question..."}
          disabled={isLoading}
          onKeyDown={handleKeyDown}
          rows="1"
        />
        <button type="submit" disabled={isLoading}>Send</button>
      </form>
    </div>
  );
}

export default App;
