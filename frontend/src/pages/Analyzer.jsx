// src/pages/Analyzer.jsx
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, MessageSquare, Upload, Mic } from "lucide-react";
import toast from "react-hot-toast";
import MessageInput from "../components/MessageInput";
import FileUploader from "../components/FileUploader";
import ResultCard from "../components/ResultCard";
import EducationPanel from "../components/EducationPanel";
import ComplaintForm from "../components/ComplaintForm";
import { fakeResult, fakeSafe } from "../mockData";

// Same animation variants for all tabs
const tabVariants = {
  initial: {
    opacity: 0,
    y: 30
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: "easeOut"
    }
  },
  exit: {
    opacity: 0,
    y: -30,
    transition: {
      duration: 0.3,
      ease: "easeIn"
    }
  }
};

export default function Analyzer() {
  const [activeTab, setActiveTab] = useState("text");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);


  const handleAnalyze = async (text) => {
    setLoading(true);
    setResult(null);
    try {
      const response = await fetch("http://localhost:5000/analyze/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      const data = await response.json();
      console.log("Analysis response:", data);

      // ✅ Check for error field from backend
      if (data.error) {
        if (data.error.includes("quota") || data.error.includes("429")) {
          toast.error("⏳ Gemini quota hit. Test with HBL/OTP messages — those work offline!");
        } else {
          toast.error("❌ " + data.error);
        }
        return; // ✅ Don't setResult — stops ResultCard from crashing
      }

      setResult(data);
      toast.success("Analysis complete!");

    } catch (err) {
      if (err.message.includes("Failed to fetch")) {
        toast.error("❌ Backend not running. Start: python main.py");
      } else {
        toast.error("❌ " + err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  // ✅ REAL FILE HANDLER (for .txt files)
  const handleFileAnalyze = async (content) => {
    setLoading(true);
    setResult(null);
    try {
      const response = await fetch("http://localhost:5000/analyze/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: content }),
      });
      const data = await response.json();
      console.log("File analysis response:", data);
      if (data.error) {
        if (data.error.includes("quota") || data.error.includes("429")) {
          toast.error("⏳ Gemini quota hit. Test with HBL/OTP messages — those work offline!");
        } else {
          toast.error("❌ " + data.error);
        }
        return; // ✅ Don't setResult — stops ResultCard from crashing
      }


      setResult(data);
      toast.success("File analysis complete!");
    }
    // ✅ Replace the catch block in handleAnalyze
    catch (err) {
      if (err.message.includes("Failed to fetch")) {
        toast.error("❌ Backend not running. Start with: python main.py");
      } else {
        toast.error("❌ " + (err.message || "Analysis failed"));
      }
    }
    finally {
      setLoading(false);
    }
  };

  // ✅ REAL AUDIO HANDLER
  const handleAudioAnalyze = async (audioFile) => {
    setLoading(true);
    setResult(null);
    try {
      toast("⏳ Transcribing audio... this takes 20-40 seconds", {
        duration: 5000,
        icon: "🎙️"
      });
      const formData = new FormData();
      formData.append("file", audioFile);
      const response = await fetch("http://localhost:5000/analyze/audio", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      console.log("Audio analysis response:", data);

      if (data.error) {
        if (data.error.includes("quota") || data.error.includes("429")) {
          toast.error("⏳ Gemini quota hit. Test with HBL/OTP messages — those work offline!");
        } else {
          toast.error("❌ " + data.error);
        }
        return; // ✅ Don't setResult — stops ResultCard from crashing
      }


      setResult(data);
      toast.success("Audio analysis complete!");
    }
    // ✅ Replace the catch block in handleAnalyze
    catch (err) {
      if (err.message.includes("Failed to fetch")) {
        toast.error("❌ Backend not running. Start with: python main.py");
      } else {
        toast.error("❌ " + (err.message || "Analysis failed"));
      }
    }
    finally {
      setLoading(false);
    }
  };


  const tabs = [
    { id: "text", label: "Paste Text", icon: MessageSquare },
    { id: "file", label: "Upload File", icon: Upload },
    { id: "audio", label: "Upload Audio", icon: Mic },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-cyan-50">
      <div className="max-w-3xl mx-auto px-4 py-12">

      {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center mb-10"
        >
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.1 }}
            className="inline-block mb-4"
          >
            <div className="bg-gradient-to-r from-blue-600 to-blue-800 p-3 rounded-2xl shadow-lg">
              <Shield className="w-12 h-12 text-white" />
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="text-4xl font-bold bg-gradient-to-r from-blue-700 to-blue-900 bg-clip-text text-transparent mb-3"
          >
            FraudGuard <span className="text-green-600">PK</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="text-gray-600 text-lg"
          >
            AI-powered scam detection for text, files & audio
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            className="flex justify-center gap-2 mt-4"
          >
            <span className="text-xs bg-blue-100 text-blue-700 px-3 py-1 rounded-full font-medium">
              PECA 2016 Compliant
            </span>
            
          </motion.div>
        </motion.div>

        {/* Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.4 }}
          className="flex gap-2 mb-6 bg-white/50 backdrop-blur rounded-xl p-1"
        >
          {tabs.map((tab) => (
            <motion.button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg font-medium transition-all duration-200
                ${activeTab === tab.id
                  ? 'bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg'
                  : 'text-gray-600 hover:bg-gray-100'
                }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </motion.button>
          ))}
        </motion.div>

        {/* Tab Content - SAME ANIMATION FOR ALL */}
        <AnimatePresence mode="wait">
          {activeTab === "text" && (
            <motion.div
              key="text"
              variants={tabVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <MessageInput onAnalyze={handleAnalyze} loading={loading} />
            </motion.div>
          )}

          {activeTab === "file" && (
            <motion.div
              key="file"
              variants={tabVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <FileUploader
                onFileAnalyze={handleFileAnalyze}
                loading={loading}
                type="text"
              />
            </motion.div>
          )}

          {activeTab === "audio" && (
            <motion.div
              key="audio"
              variants={tabVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <FileUploader
                onFileAnalyze={handleAudioAnalyze}
                loading={loading}
                type="audio"
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading Animation */}
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: -20 }}
              transition={{ duration: 0.3 }}
              className="text-center py-12"
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                className="inline-block w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full"
              />
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-sm text-gray-500 mt-3"
              >
                {activeTab === "audio" ? "Processing audio file..." : "AI analyzing message patterns..."}
              </motion.p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results Section */}
        <AnimatePresence mode="wait">
          {result && !loading && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -40 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="space-y-5 mt-6"
            >
              <ResultCard result={result} />
              <EducationPanel items={result.education} />
              {result.complaint && <ComplaintForm text={result.complaint} />}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.5 }}
          className="mt-12 pt-6 border-t border-blue-100 text-center"
        >
          <p className="text-xs text-gray-400">
            🔒 Your files are encrypted • Supports .txt, .mp3, .wav, .m4a • 
          </p>
        </motion.div>
      </div>
    </div>
  );
}