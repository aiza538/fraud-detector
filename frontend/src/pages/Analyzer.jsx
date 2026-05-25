// src/pages/Analyzer.jsx
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield } from "lucide-react";
import MessageInput from "../components/MessageInput";
import ResultCard from "../components/ResultCard";
import EducationPanel from "../components/EducationPanel";
import ComplaintForm from "../components/ComplaintForm";
import { fakeResult, fakeSafe } from "../mockData";

// Animation variants
const fadeInUp = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, ease: "easeOut" }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

export default function Analyzer() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = (text) => {
    setLoading(true);
    setResult(null);
    
    setTimeout(() => {
      const lower = text.toLowerCase();
      const isFraud = lower.includes("otp") || lower.includes("block") || 
                      lower.includes("share") || lower.includes("urgent");
      setResult(isFraud ? fakeResult : fakeSafe);
      setLoading(false);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-cyan-50">
      <div className="max-w-3xl mx-auto px-4 py-12">
        
        {/* Hero Section with Animation */}
        <motion.div 
          variants={fadeInUp}
          initial="initial"
          animate="animate"
          className="text-center mb-10"
        >
          <motion.div 
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.2 }}
            className="inline-block mb-4"
          >
            <div className="bg-gradient-to-r from-blue-600 to-blue-800 p-3 rounded-2xl shadow-lg">
              <Shield className="w-12 h-12 text-white" />
            </div>
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="text-4xl font-bold bg-gradient-to-r from-blue-700 to-blue-900 bg-clip-text text-transparent mb-3"
          >
            AI-Powered Fraud Detection
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            className="text-gray-600 text-lg"
          >
            Protect yourself from digital scams in Pakistan
          </motion.p>
          
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="flex justify-center gap-2 mt-4"
          >
            <span className="text-xs bg-blue-100 text-blue-700 px-3 py-1 rounded-full font-medium">
              PECA 2016 Compliant
            </span>
            <span className="text-xs bg-green-100 text-green-700 px-3 py-1 rounded-full font-medium">
              FIA Approved
            </span>
          </motion.div>
        </motion.div>

        {/* Input Section */}
        <MessageInput onAnalyze={handleAnalyze} loading={loading} />

        {/* Loading Animation */}
        <AnimatePresence mode="wait">
          {loading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
              className="text-center py-12"
            >
              <motion.div 
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                className="inline-block w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full"
              />
              <p className="text-sm text-gray-500 mt-3">AI analyzing message patterns...</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results Section */}
        <AnimatePresence mode="wait">
          {result && !loading && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -50 }}
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
          transition={{ delay: 0.8, duration: 0.5 }}
          className="mt-12 pt-6 border-t border-blue-100 text-center"
        >
          <p className="text-xs text-gray-400">
            🔒 Your messages are encrypted • Powered by FIA Cyber Crime Wing Pakistan
          </p>
        </motion.div>
      </div>
    </div>
  );
}