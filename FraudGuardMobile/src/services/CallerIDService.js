// Utility function for Levenshtein distance
const levenshtein = (a, b) => {
  const matrix = [];
  for (let i = 0; i <= b.length; i++) matrix[i] = [i];
  for (let j = 0; j <= a.length; j++) matrix[0][j] = j;
  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      const cost = a[j - 1] === b[i - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost
      );
    }
  }
  return matrix[b.length][a.length];
};

const VERIFIED_AUTHORITIES = {
  'FBR':    ['03111825662', '051-111772772'],
  'SBP':    ['021-99221010', '021-99221011'],
  'NADRA':  ['1700', '051-9106316'],
  'FIA':    ['1717'],
  'BISP':   ['0800-26477'],
};

export function checkCallerID(incomingNumber) {
  const cleaned = incomingNumber.replace(/[\s\-\(\)]/g, '');
  
  for (const [authority, numbers] of Object.entries(VERIFIED_AUTHORITIES)) {
    for (const official of numbers) {
      const officialCleaned = official.replace(/[\s\-\(\)]/g, '');
      
      if (cleaned === officialCleaned) {
        return { status: 'verified', authority };
      }
      
      if (levenshtein(cleaned, officialCleaned) <= 2 && cleaned.length === officialCleaned.length) {
        return { 
          status: 'spoofed', 
          authority, 
          warning: `⚠️ This number is similar to ${authority} but is fake.`
        };
      }
    }
  }
  return { status: 'unknown' };
}