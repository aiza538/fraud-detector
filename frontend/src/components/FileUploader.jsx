// src/components/FileUploader.jsx
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Mic, X, CheckCircle, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";

export default function FileUploader({ onFileAnalyze, loading, type }) {
  const [file, setFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const selectedFile = acceptedFiles[0];
    
    if (type === 'text' && !selectedFile.name.endsWith('.txt')) {
      toast.error("Please upload a .txt file only");
      return;
    }
    
    if (type === 'audio' && !selectedFile.type.startsWith('audio/')) {
      toast.error("Please upload an audio file (.mp3, .wav, .m4a)");
      return;
    }
    
    setFile(selectedFile);
    
    if (type === 'text') {
      const reader = new FileReader();
      reader.onload = (e) => {
        setFileContent(e.target.result);
      };
      reader.readAsText(selectedFile);
    } else {
      setFileContent(null);
    }
    
    toast.success(`File loaded: ${selectedFile.name}`);
  }, [type]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: type === 'text' ? { 'text/plain': ['.txt'] } : { 'audio/*': ['.mp3', '.wav', '.m4a', '.mp4'] },
    maxFiles: 1
  });

  const handleAnalyze = () => {
    if (!file) {
      toast.error("Please select a file first");
      return;
    }
    
    if (type === 'text' && fileContent) {
      onFileAnalyze(fileContent);
    } else if (type === 'audio') {
      onFileAnalyze(file);
    }
  };

  const removeFile = () => {
    setFile(null);
    setFileContent(null);
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
          {type === 'text' ? (
            <FileText className="w-5 h-5 text-white" />
          ) : (
            <Mic className="w-5 h-5 text-white" />
          )}
        </div>
        <div>
          <h3 className="font-semibold text-gray-700">
            Upload {type === 'text' ? 'Text File' : 'Audio File'}
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            {type === 'text' 
              ? 'Upload .txt files containing suspicious messages' 
              : 'Upload .mp3, .wav, .m4a files (max 10MB)'}
          </p>
        </div>
      </div>

      {/* Drop Zone */}
      <motion.div
        whileHover={{ scale: 1.01 }}
        transition={{ duration: 0.2 }}
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200
          ${isDragActive 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/50'
          }`}
      >
        <input {...getInputProps()} />
        <motion.div
          animate={{ y: isDragActive ? -5 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <Upload className={`w-10 h-10 mx-auto mb-3 transition-colors duration-200 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`} />
          {isDragActive ? (
            <p className="text-sm text-blue-600">Drop the file here...</p>
          ) : (
            <div>
              <p className="text-sm text-gray-600">
                Drag & drop or <span className="text-blue-600 font-medium">browse</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {type === 'text' ? 'Supported: .txt' : 'Supported: .mp3, .wav, .m4a'}
              </p>
            </div>
          )}
        </motion.div>
      </motion.div>

      {/* Selected File Preview */}
      <AnimatePresence mode="wait">
        {file && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.3, type: "spring", stiffness: 400 }}
            className="mt-4 p-3 bg-gradient-to-r from-gray-50 to-blue-50/30 rounded-xl"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <motion.div
                  initial={{ rotate: -180, scale: 0 }}
                  animate={{ rotate: 0, scale: 1 }}
                  transition={{ type: "spring", stiffness: 300 }}
                >
                  {type === 'text' ? (
                    <FileText className="w-8 h-8 text-blue-500" />
                  ) : (
                    <Mic className="w-8 h-8 text-green-500" />
                  )}
                </motion.div>
                <div>
                  <p className="text-sm font-medium text-gray-700">{file.name}</p>
                  <p className="text-xs text-gray-400">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                {type === 'text' && fileContent && (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      const preview = fileContent.substring(0, 200);
                      toast.custom((t) => (
                        <div className="bg-white rounded-lg shadow-xl p-4 max-w-md">
                          <p className="text-sm font-medium mb-2">File Preview:</p>
                          <p className="text-xs text-gray-600">{preview}...</p>
                          <button onClick={() => toast.dismiss(t.id)} className="mt-2 text-blue-500 text-xs">Close</button>
                        </div>
                      ));
                    }}
                    className="p-1.5 hover:bg-gray-200 rounded-lg transition-all duration-200"
                  >
                    <FileText className="w-4 h-4 text-gray-500" />
                  </motion.button>
                )}
                <motion.button
                  whileHover={{ scale: 1.05, backgroundColor: "#fee2e2" }}
                  whileTap={{ scale: 0.95 }}
                  onClick={removeFile}
                  className="p-1.5 hover:bg-red-100 rounded-lg transition-all duration-200"
                >
                  <X className="w-4 h-4 text-red-500" />
                </motion.button>
              </div>
            </div>
            {type === 'text' && fileContent && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                transition={{ duration: 0.3 }}
                className="mt-2 pt-2 border-t border-gray-200"
              >
                <p className="text-xs text-gray-500 line-clamp-2">
                  {fileContent.substring(0, 150)}...
                </p>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Analyze Button */}
      <AnimatePresence>
        {file && (
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.3 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleAnalyze}
            disabled={loading}
            className="mt-4 w-full bg-gradient-to-r from-blue-600 to-blue-800 text-white py-3 rounded-xl flex items-center justify-center gap-2 shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50"
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
                <CheckCircle className="w-4 h-4" />
                <span>Analyze {type === 'text' ? 'Text' : 'Audio'} File</span>
              </>
            )}
          </motion.button>
        )}
      </AnimatePresence>
    </motion.div>
  );
}