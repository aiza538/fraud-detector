// src/components/MessageInput.jsx
import { useState } from "react";
import { Send, Mic, FileText, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";

export default function MessageInput({ onAnalyze, loading }) {
  const [text, setText] = useState("");
  const [charCount, setCharCount] = useState(0);
  const [isFocused, setIsFocused] = useState(false);

  const handleTextChange = (e) => {
    setText(e.target.value);
    setCharCount(e.target.value.length);
  };

  const handleSubmit = () => {
    if (!text.trim()) {
      toast.error("Please paste a message to analyze");
      return;
    }
    if (text.length < 20) {
      toast.error("Message seems too short. Please paste the complete message");
      return;
    }
    onAnalyze(text);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-2 rounded-xl">
          <FileText className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-700">Paste Suspicious Message</h3>
          <p className="text-xs text-gray-400 mt-0.5">SMS, WhatsApp, or social media messages</p>
        </div>
      </div>

      <div className="relative">
        <motion.textarea
          animate={{ 
            borderColor: isFocused ? "#3b82f6" : "#e5e7eb",
            boxShadow: isFocused ? "0 0 0 3px rgba(59,130,246,0.1)" : "none"
          }}
          transition={{ duration: 0.2 }}
          rows={6}
          value={text}
          onChange={handleTextChange}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Paste suspicious message here...&#10;&#10;Example: 'Assalam-o-Alaikum, main HBL security team se bol raha hoon. Aap ka account block ho raha hai. Fooran OTP share karein...'"
          className="w-full border rounded-xl p-4 text-sm resize-none focus:outline-none bg-gray-50 text-gray-700 transition-all duration-200"
        />
        <AnimatePresence>
          {charCount > 0 && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="absolute bottom-3 right-3 flex items-center gap-2"
            >
              <div className="flex items-center gap-1 bg-white/80 backdrop-blur px-2 py-1 rounded-full">
                <AlertCircle className="w-3 h-3 text-gray-400" />
                <span className="text-[10px] text-gray-400">{charCount} characters</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex justify-between items-center mt-4">
        <div className="flex gap-2">
          {["Roman Urdu", "English", "Urdu", "Mix"].map((lang, idx) => (
            <motion.button
              key={lang}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05, duration: 0.2 }}
              whileHover={{ scale: 1.05, backgroundColor: "#eff6ff", color: "#2563eb" }}
              whileTap={{ scale: 0.95 }}
              className="text-xs bg-white text-gray-500 border border-gray-200 px-3 py-1.5 rounded-lg transition-all duration-200"
            >
              {lang}
            </motion.button>
          ))}
        </div>
        
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleSubmit}
          disabled={loading || !text.trim()}
          className="bg-gradient-to-r from-blue-600 to-blue-800 text-white px-6 py-2.5 rounded-xl flex items-center gap-2 shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50"
        >
          {loading ? (
            <>
              <motion.div 
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
              />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span>Detect Fraud</span>
            </>
          )}
        </motion.button>
      </div>
    </motion.div>
  );
}