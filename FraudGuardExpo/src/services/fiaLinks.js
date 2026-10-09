// src/services/fiaLinks.js
//
// FIA Cyber Wing tak complaint "ponchne" ke official tareeqe. Pakistan ka
// koi public API ya scam-number DB nahi hai, is liye complaint ka rasta yehi
// official channels hain — in numbers/URLs ka koi verified public source:
//   - complaint portal : https://complaint.fia.gov.pk/?view=complaint
//   - cyber helpdesk   : helpdesk.cyber@fia.gov.pk (fia.gov.pk/ccw)
//   - helpline         : 1991  (Mon–Fri 8:00–16:00, fia.gov.pk/ccw)
//   - general FIA      : 051-111-345-786 (fia.gov.pk)
//   - 15 CCRC centres  : fia.gov.pk/ccw (6 zones)
//
// NOTE: 111-345-786 backend ke LEGITIMATE_DIRECTORY me "FIA" ke naam se hai,
// magar wo CALL number hai, helpline number nahi. Email/portal alag hai.

export const FIA_PORTAL_URL = "https://complaint.fia.gov.pk/?view=complaint";
export const FIA_EMAIL = "helpdesk.cyber@fia.gov.pk";
export const FIA_CYBER_HELPLINE = "1991";
export const FIA_GENERAL_HELPLINE = "051-111-345-786";
export const FIA_CCRC_INFO_URL = "https://www.fia.gov.pk/ccw";
export const PTA_COMPLAINT_EMAIL = "complaint@pta.gov.pk";
export const PTA_HELPLINE = "0800-55055";

/** Complaint text ko email body mein bhejne ke liye. */
export function buildEmailBody({ number, message, channel }) {
  const rows = [
    "Respected FIA Cyber Crime Wing,",
    "",
    "Main ek cybercrime ka shikayat darj karna chahta/chahti hoon. Neeche diye gaye tafseel ke mutabiq meri report hai:",
    "",
    `Subject (kya hua):        ${message}`,
    `Suspect ka number:       ${number || "maloom nahi"}`,
    `Jahan se aaya (channel): ${channel || "WhatsApp / SMS"}`,
    `Date of incident:        ${new Date().toLocaleDateString("en-PK")}`,
    "",
    "Agar zaroorat hoi to main screen shots aur call recording submit kar sakta/sakti hoon.",
    "",
    "Regards,",
  ];
  return rows.join("\n");
}

/** `mailto:` URL — kuch email clients `body` ko nahi padhte, is liye encode. */
export function buildEmailLink({ number, message, channel }) {
  const subject = `Cyber Crime Complaint: ${message}`.slice(0, 120);
  const body = buildEmailBody({ number, message, channel });
  return `mailto:${FIA_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
