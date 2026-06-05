// src/content.js
console.log("🛡️ FraudGuard PK Content Script loaded.");

// Create a floating scan button
const scanBtn = document.createElement("button");
scanBtn.innerText = "🛡️ Scan Chat";
scanBtn.style.cssText = "position:fixed; bottom:20px; right:20px; z-index:9999; padding:10px 15px; background:#2563eb; color:white; border-radius:8px; font-weight:bold; cursor:pointer; border:none; box-shadow:0 4px 6px rgba(0,0,0,0.1);";
document.body.appendChild(scanBtn);

scanBtn.addEventListener("click", () => {
    scanBtn.innerText = "⏳ Scanning...";
    
    // Grabs text from the page (This targets generic spans, can be tweaked for WhatsApp specifically)
    // WhatsApp Web chat bubbles usually have specific classes like ._amk4
    const chatElements = document.querySelectorAll('span[dir="ltr"]'); 
    let fullChat = "";
    chatElements.forEach(el => fullChat += el.innerText + "\n");
    
    // We only care about the most recent messages (last 2000 chars)
    const recentChat = fullChat.slice(-2000);

    if (recentChat.length < 10) {
        alert("No chat detected on this screen.");
        scanBtn.innerText = "🛡️ Scan Chat";
        return;
    }

    // Send to background script
    chrome.runtime.sendMessage({ action: "analyzeText", text: recentChat }, (response) => {
        scanBtn.innerText = "🛡️ Scan Chat";
        if (response.success) {
            const data = response.data;
            if (data.fraud) {
                alert(`🚨 FRAUD DETECTED!\nType: ${data.type}\nConfidence: ${data.confidence}%\nTactics: ${data.tactics.join(", ")}`);
                // Future upgrade: Inject a red border around the specific scam message in the DOM!
            } else {
                alert("✅ This chat appears safe.");
            }
        } else {
            alert("Error connecting to FraudGuard backend.");
        }
    });
});
