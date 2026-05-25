export default function FraudBadge({ fraud, confidence }) {
  if (fraud === null) return null;
  const color = fraud
    ? "bg-red-100 text-red-700 border-red-300"
    : "bg-green-100 text-green-700 border-green-300";
  const label = fraud ? "Fraud Detected" : "Safe Message";
  const icon = fraud ? "⚠️" : "✅";
  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${color}`}>
      <span className="text-2xl">{icon}</span>
      <div>
        <p className="font-semibold text-sm">{label}</p>
        <p className="text-xs opacity-70">Confidence: {confidence}%</p>
      </div>
    </div>
  );
}