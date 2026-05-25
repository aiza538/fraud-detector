export const fakeResult = {
  fraud: true,
  type: "HBL Vishing Attack",
  confidence: 94,
  peca: "PECA 2016 — Section 17",
  attack: "Vishing",
  target: "HBL Bank",
  language: "Roman Urdu",
  tactics: ["Urgency", "Authority Impersonation", "OTP Phishing"],
  education: [
    "Real banks never call to ask for your OTP.",
    "Scammer pretends to be bank officer to build trust.",
    "They create urgency so you act without thinking.",
    "If you get this call, hang up and call bank directly.",
  ],
  complaint: `TO: FIA Cyber Crime Wing\nSUBJECT: Vishing Fraud — HBL Impersonation\n\nI received a call claiming to be HBL security team asking for my OTP.\n\nLaw: PECA 2016, Section 17`,
};

export const fakeSafe = {
  fraud: false,
  type: "Legitimate Bank SMS",
  confidence: 96,
  peca: "No violation",
  attack: "None",
  target: "HBL Customer",
  language: "English",
  tactics: [],
  education: [
    "This message follows real bank OTP format.",
    "It warns you NOT to share OTP — real banks do this.",
    "No urgency pressure, no personal data request.",
  ],
  complaint: null,
};
