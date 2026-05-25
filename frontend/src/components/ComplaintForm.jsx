export default function ComplaintForm({ text }) {
  if (!text) return null;
  const download = () => {
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "FIA_Complaint.txt";
    a.click();
  };
  return (
    <div className="bg-white/90 backdrop-blur-sm border border-dashed border-blue-300 rounded-2xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <p className="font-semibold text-sm flex items-center gap-2">
          <span>📄</span> Auto-generated FIA Complaint
        </p>
        <button
          onClick={download}
          className="text-xs bg-blue-50 text-blue-700 border border-blue-300 px-3 py-1.5 rounded-lg hover:bg-blue-100 transition-all"
        >
          Download
        </button>
      </div>
      <pre className="text-xs text-gray-500 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap font-mono">
        {text}
      </pre>
    </div>
  );
}