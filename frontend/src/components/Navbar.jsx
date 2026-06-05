// src/components/Navbar.jsx
import { Shield, Bell } from "lucide-react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export default function Navbar() {
  return (
    <motion.nav 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
      className="sticky top-0 z-50 bg-gradient-to-r from-blue-900 via-blue-800 to-blue-900 shadow-xl"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo Section */}
          <Link to="/" className="flex items-center gap-3 group">
            <motion.div 
              whileHover={{ scale: 1.05, rotate: 5 }}
              transition={{ type: "spring", stiffness: 400 }}
              className="bg-gradient-to-r from-blue-400 to-cyan-400 p-2 rounded-xl shadow-lg"
            >
              <Shield className="w-5 h-5 text-white" />
            </motion.div>
            <div>
              <h1 className="font-bold text-lg text-white tracking-tight">
                FraudGuard <span className="text-blue-300">PK</span>
              </h1>
              <p className="text-[9px] text-blue-200 tracking-wShieldide">FIA Cyber Crime Wing</p>
            </div>
          </Link>

          {/* Notification */}
          <motion.button 
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="p-2 hover:bg-white/10 rounded-lg transition-all duration-300 relative"
          >
            <Bell className="w-5 h-5 text-blue-200" />
            <motion.span 
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ repeat: Infinity, duration: 2 }}
              className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"
            ></motion.span>
          </motion.button>
        </div>
      </div>
    </motion.nav>
  );
}