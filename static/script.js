let currentIdea = "";

async function callAPI(endpoint, idea) {
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const resultContent = document.getElementById('result-content');
    const resultTitle = document.getElementById('result-title');

    loading.classList.remove('hidden');
    results.classList.add('hidden');

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idea: idea })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Something went wrong');
        }

        // Set title based on endpoint
        if (endpoint.includes('validate')) resultTitle.textContent = "Idea Validation";
        else if (endpoint.includes('market')) resultTitle.textContent = "Market Research";
        else resultTitle.textContent = "Investor Pitch";

        resultContent.innerHTML = data.result.replace(/\n/g, '<br>');
        results.classList.remove('hidden');

    } catch (error) {
        resultContent.innerHTML = `<strong style="color:red;">Error:</strong> ${error.message}`;
        results.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
    }
}

function validateIdea() {
    const ideaInput = document.getElementById('idea').value.trim();
    if (!ideaInput) {
        alert("Please enter your startup idea!");
        return;
    }
    currentIdea = ideaInput;
    callAPI('/validate-idea', ideaInput);
}

function marketResearch() {
    const ideaInput = document.getElementById('idea').value.trim();
    if (!ideaInput) {
        alert("Please enter your startup idea!");
        return;
    }
    currentIdea = ideaInput;
    callAPI('/market-research', ideaInput);
}

function generatePitch() {
    const ideaInput = document.getElementById('idea').value.trim();
    if (!ideaInput) {
        alert("Please enter your startup idea!");
        return;
    }
    currentIdea = ideaInput;
    callAPI('/generate-pitch', ideaInput);
}

// Toggle Profile Dropdown
function toggleDropdown() {
  const dropdown = document.getElementById('profile-dropdown');
  dropdown.classList.toggle('show');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
  const dropdown = document.getElementById('profile-dropdown');
  const avatar = document.querySelector('.profile-avatar');
  
  if (!avatar.contains(e.target)) {
    dropdown.classList.remove('show');
  }
});