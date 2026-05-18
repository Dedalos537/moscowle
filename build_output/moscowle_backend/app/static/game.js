const gameArea = document.getElementById('game-area');
const target = document.getElementById('target');
const startBtn = document.getElementById('start-btn');
const resultBox = document.getElementById('result-box');

let startTime, endTime;
let reactionTimes = [];
let attemps = 0;
let maxAttemps = 5;
let hits = 0;

startBtn.addEventListener('click', startGame);

target.addEventListener('click', () => {
    endTime = Date.now();
    const timeTaken = endTime - startTime;
    reactionTimes.push(timeTaken);
    document.getElementById('time-display').innerText = timeTaken;
    hits++;
    document.getElementById('score-display').innerText = hits + '/' + maxAttemps;
    target.style.display = 'none';

    nextRound();
});

gameArea.addEventListener('click', () => {
    if (endTime.target !== targer && targer.style.display == 'block'){
        reactionTimes.push(2000);
        targer.style.display = 'none';
        nextRound();
    }
});

function startGame(){
    startBtn.style.display = 'none';
    resultBox.style.display = 'none';
    reactionTimes = [];
    attemps = 0;
    hits = 0;
    document.getElementById('score-display').innerText = hits + '/' + maxAttemps;
    nextRound();
}

function nextRound(){
    attemps++;
    if (attemps > maxAttemps){
        endGame();
        return;
    }
    const randomDelay = Math.floor(Math.random() * 2000) + 500;

    setTimeout(() => {
        const x = Math.floor(Math.random() * (gameArea.clientWidth - 50));
        const y = Math.floor(Math.random() * (gameArea.clientHeight - 50));
        target.style.left = x + 'px';
        target.style.top = y + 'px';
        target.style.display = 'block';
        startTime = Date.now();
    }, randomDelay);
}

function endGame(){
    const totalTime = reactionTimes.reduce((a, b) => a + b, 0);
    const avgTime = Math.round(totalTime / reactionTimes.length);
    const accuracy = (hits / maxAttemps) * 100;

    document.getElementById('final-acc').innerText = accuracy.toFixed(1);
    document.getElementById('final-time').innerText = avgTime.toFixed(0);

    fetch('/api/save_game', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            average_time: avgTime,
            accuracy: accuracy
        })
    }).then(response => response.json())
      .then(data => {
        resultBox.style.display = 'block';
        const aiText = document.getElementById('ai-recommendation');
        aiText.innerText = data.recommendation;
        if (data.code == 1) aiText.textContent.style.color ='var(--color-success)';
        else if (data.code == 2) aiText.style.color='var(--color-error)';
        else aiText.style.color='var(--color-primary)';
    });
    
}