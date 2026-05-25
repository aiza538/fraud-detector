export default function EducationPanel({ items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="bg-white/90 backdrop-blur-sm border border-blue-100 rounded-2xl p-5 shadow-xl">
      <p className="font-semibold text-sm mb-3 flex items-center gap-2">
        <span>💡</span> How this scam works — protect yourself
      </p>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex gap-2 text-sm text-gray-500">
            <span className="text-blue-500 mt-0.5">✓</span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}