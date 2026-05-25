// src/components/ResultCard.jsx
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle, Target, Scale, Languages, Zap } from "lucide-react";

export default function ResultCard({ result }) {
  if (!result) return null;

  const stats = [
    { icon: Target, label: "Attack Type", value: result.type, color: "text-red-500", delay: 0.1 },
    { icon: Scale, label: "Legal Reference", value: result.peca, color: "text-blue-500", delay: 0.2 },
    { icon: Languages, label: "Language", value: result.language, color: "text-purple-500", delay: 0.3 },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, type: "spring", stiffness: 200 }}
      className="bg-white rounded-2xl p-6 space-y-5 shadow-xl border border-gray-100"
    >
      {/* Header Badge */}
      <motion.div 
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className={`flex items-center gap-3 p-4 rounded-xl ${result.fraud ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'}`}
      >
        <motion.div
          initial={{ rotate: -180, scale: 0 }}
          animate={{ rotate: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 300, delay: 0.2 }}
        >
          {result.fraud ? (
            <AlertTriangle className="w-8 h-8 text-red-500" />
          ) : (
            <CheckCircle className="w-8 h-8 text-green-500" />
          )}
        </motion.div>
        <div>
          <h2 className={`text-xl font-bold ${result.fraud ? 'text-red-700' : 'text-green-700'}`}>
            {result.fraud ? "⚠️ Fraud Detected" : "✅ Safe Message"}
          </h2>
          <p className="text-sm opacity-70">Confidence: {result.confidence}% • FIA Verified</p>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-3">
        {stats.map((stat) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: stat.delay, duration: 0.3 }}
            whileHover={{ y: -5, transition: { duration: 0.2 } }}
            className="bg-gray-50 rounded-xl p-3 cursor-pointer"
          >
            <stat.icon className={`w-4 h-4 ${stat.color} mb-2`} />
            <p className="text-[10px] text-gray-400 uppercase tracking-wider">{stat.label}</p>
            <p className="text-xs font-medium mt-1">{stat.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Tactics Tags */}
      {result.tactics.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
            <Zap className="w-3 h-3" /> Manipulation Tactics Detected
          </p>
          <div className="flex flex-wrap gap-2">
            {result.tactics.map((tactic, idx) => (
              <motion.span
                key={tactic}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.5 + idx * 0.1, type: "spring", stiffness: 300 }}
                whileHover={{ scale: 1.05 }}
                className="bg-red-100 text-red-700 text-xs px-3 py-1 rounded-full border border-red-200 cursor-pointer"
              >
                {tactic}
              </motion.span>
            ))}
          </div>
        </motion.div>
      )}

      {/* Targeted Entity */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="bg-yellow-50 border border-yellow-200 rounded-xl p-3"
      >
        <p className="text-xs text-yellow-700">
          🎯 <strong>Targeted:</strong> {result.target}
        </p>
      </motion.div>
    </motion.div>
  );
}