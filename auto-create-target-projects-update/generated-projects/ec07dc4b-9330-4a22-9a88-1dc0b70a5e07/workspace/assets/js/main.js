const canvas = document.getElementById('particle-bg');
const ctx = canvas.getContext('2d');
let particles = [];
let isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    initParticles();
}

function initParticles() {
    particles = [];
    const count = Math.min(20, Math.floor(window.innerWidth * window.innerHeight / 30000));
    for (let i = 0; i < count; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: Math.random() * 3 + 1,
            speedX: (Math.random() - 0.5) * 0.5,
            speedY: (Math.random() - 0.5) * 0.5,
            opacity: Math.random() * 0.3 + 0.1
        });
    }
}

function drawParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const color = isDarkMode ? '255, 255, 255' : '0, 0, 0';
    particles.forEach(p => {
        ctx.fillStyle = `rgba(${color}, ${p.opacity})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        p.x += p.speedX;
        p.y += p.speedY;
        if (p.x < 0 || p.x > canvas.width) p.speedX *= -1;
        if (p.y < 0 || p.y > canvas.height) p.speedY *= -1;
    });
    requestAnimationFrame(drawParticles);
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    isDarkMode = e.matches;
});

new ResizeObserver(resizeCanvas).observe(document.body);
resizeCanvas();
drawParticles();