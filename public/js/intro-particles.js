function mountIntroParticles(canvasId = 'intro-particle-canvas') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const pointer = { active: false, x: 0, y: 0 };

  let width = 1;
  let height = 1;
  let particles = [];
  let raf = null;
  let last = 0;

  const colors = [
    '144,103,198',
    '141,134,201',
    '202,196,206',
  ];

  function seededRandom() {
    let seed = 271828;
    return () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const nextWidth = Math.max(1, Math.round(rect.width));
    const nextHeight = Math.max(1, Math.round(rect.height));
    if (nextWidth === width && nextHeight === height) return;

    width = nextWidth;
    height = nextHeight;

    const scale = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    ctx.setTransform(scale, 0, 0, scale, 0, 0);

    const rand = seededRandom();
    const count = Math.max(42, Math.min(86, Math.round((width * height) / 7400)));

    particles = Array.from({ length: count }, (_, index) => {
      const x = width * (0.12 + rand() * 0.76);
      const y = height * (0.18 + rand() * 0.64);

      return {
        x,
        y,
        homeX: x,
        homeY: y,
        vx: (rand() - 0.5) * 0.18,
        vy: (rand() - 0.5) * 0.18,
        r: 1.3 + rand() * 2.4,
        orbit: 8 + rand() * 28,
        phase: rand() * Math.PI * 2,
        speed: 0.38 + rand() * 0.86,
        color: colors[index % colors.length],
      };
    });
  }

  function update(now) {
    const dt = last ? Math.min(2.2, (now - last) / 16.67) : 1;
    last = now;

    const t = now * 0.001;
    const focusX = width * 0.5;
    const focusY = height * 0.52;

    for (const p of particles) {
      const targetX = p.homeX + Math.sin(t * p.speed + p.phase) * p.orbit;
      const targetY = p.homeY + Math.cos(t * p.speed * 0.72 + p.phase) * p.orbit * 0.44;

      p.vx += (targetX - p.x) * 0.006 * dt;
      p.vy += (targetY - p.y) * 0.006 * dt;

      p.vx += (focusX - p.x) * 0.00042 * dt;
      p.vy += (focusY - p.y) * 0.00032 * dt;

      if (pointer.active) {
        const dx = p.x - pointer.x;
        const dy = p.y - pointer.y;
        const distance = Math.hypot(dx, dy);

        if (distance > 0 && distance < 132) {
          const force = Math.pow(1 - distance / 132, 2);
          p.vx += (dx / distance) * force * 1.8 * dt;
          p.vy += (dy / distance) * force * 1.8 * dt;
        }
      }

      p.vx *= Math.pow(0.92, dt);
      p.vy *= Math.pow(0.92, dt);
      p.x += p.vx * dt;
      p.y += p.vy * dt;
    }
  }

  function draw(now) {
    ctx.clearRect(0, 0, width, height);

    const linkLimit = Math.max(86, Math.min(126, width * 0.16));
    ctx.lineWidth = 0.9;

    for (let i = 0; i < particles.length; i += 1) {
      for (let j = i + 1; j < particles.length; j += 1) {
        const a = particles[i];
        const b = particles[j];
        const distance = Math.hypot(a.x - b.x, a.y - b.y);
        if (distance > linkLimit) continue;

        const opacity = Math.pow(1 - distance / linkLimit, 2) * 0.2;
        ctx.strokeStyle = `rgba(${a.color}, ${opacity})`;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }

    for (const p of particles) {
      const pulse = 0.75 + Math.sin(now * 0.002 + p.phase) * 0.16;

      ctx.fillStyle = `rgba(${p.color}, 0.58)`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * pulse, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = 'rgba(247,236,225,0.70)';
      ctx.beginPath();
      ctx.arc(p.x - p.r * 0.18, p.y - p.r * 0.2, Math.max(0.55, p.r * 0.32), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function frame(now) {
    resize();

    if (reduceMotion.matches) {
      draw(now);
      raf = null;
      return;
    }

    update(now);
    draw(now);
    raf = requestAnimationFrame(frame);
  }

  document.addEventListener('pointermove', (event) => {
    const rect = canvas.getBoundingClientRect();
    const inside =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;

    if (!inside) {
      pointer.active = false;
      return;
    }

    pointer.active = true;
    pointer.x = event.clientX - rect.left;
    pointer.y = event.clientY - rect.top;
  });

  document.addEventListener('pointerleave', () => {
    pointer.active = false;
  });

  window.addEventListener('resize', () => {
    resize();
    if (reduceMotion.matches && !raf) raf = requestAnimationFrame(frame);
  });

  reduceMotion.addEventListener?.('change', () => {
    if (!raf) raf = requestAnimationFrame(frame);
  });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden && raf) {
      cancelAnimationFrame(raf);
      raf = null;
    } else if (!document.hidden && !raf) {
      raf = requestAnimationFrame(frame);
    }
  });

  resize();
  raf = requestAnimationFrame(frame);
}

mountIntroParticles();
