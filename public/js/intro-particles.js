function mountIntroParticles(canvasId = 'intro-particle-canvas') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const pointer = { active: false, x: 0, y: 0 };
  const typing = {
    active: false,
    x: 0,
    y: 0,
    energy: 0,
    ring: 0,
    spaceEnergy: 0,
    spaceWave: 0,
    spaceX: 0,
    spaceY: 0,
    spaceWidth: 1,
    burstUntil: 0,
    lastValueLength: 0,
  };

  let width = 1;
  let height = 1;
  let particles = [];
  let sparks = [];
  let raf = null;
  let last = 0;

  // Luminescent nodes for Antigravity Neuro-Aesthetic
  function getThemeColors() {
    const isDarkMode = document.body.getAttribute('data-theme') === 'dark' || 
                       (document.body.classList.contains('dark-mode') && document.body.getAttribute('data-theme') !== 'light');
    return isDarkMode ? [
      '158,139,255', // Bright lavender
      '144,103,198', // Deep purple
      '60,221,199',  // Accent mint
      '255,255,255', // Pure light
    ] : [
      '110,80,180',  // Darker lavender
      '90,50,150',   // Deep solid purple
      '40,180,150',  // Darker mint
      '144,103,198', // Mid purple instead of pure white
    ];
  }

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
    const count = Math.max(30, Math.min(60, Math.round((width * height) / 9000))); // Fewer particles, more void

    particles = Array.from({ length: count }, (_, index) => {
      const x = width * (0.12 + rand() * 0.76);
      const y = height * (0.18 + rand() * 0.64);

      return {
        x,
        y,
        homeX: x,
        homeY: y,
        vx: (rand() - 0.5) * 0.1, // Slower base velocity
        vy: (rand() - 0.5) * 0.1,
        r: 1.5 + rand() * 3.5, // Slightly larger nodes
        orbit: 10 + rand() * 40,
        phase: rand() * Math.PI * 2,
        speed: 0.15 + rand() * 0.4, // Slower orbit (Intellectual calm)
        colorIndex: index % 4,
      };
    });
  }

  function getThresholdFields() {
    return ['hero-single-input-field', 'hero-starting-map-field']
      .map((id) => document.getElementById(id))
      .filter((field) => field instanceof HTMLTextAreaElement);
  }

  function getActiveThresholdField() {
    const fields = getThresholdFields();
    return fields.includes(document.activeElement)
      ? document.activeElement
      : (fields[1] || fields[0] || null);
  }

  function getTypingFocus() {
    const field = getActiveThresholdField();
    const canvasRect = canvas.getBoundingClientRect();
    const fieldRect = field?.getBoundingClientRect?.();

    if (!fieldRect) {
      return { x: width * 0.5, y: height * 0.58 };
    }

    const styles = window.getComputedStyle(field);
    const fontSize = Number.parseFloat(styles.fontSize) || 16;
    const paddingLeft = Number.parseFloat(styles.paddingLeft) || 16;
    const paddingRight = Number.parseFloat(styles.paddingRight) || 16;
    const selectionIndex = typeof field.selectionStart === 'number' ? field.selectionStart : field.value.length;
    const currentLine = field.value.slice(0, selectionIndex).split('\n').pop() || '';
    ctx.save();
    ctx.font = `${styles.fontStyle} ${styles.fontWeight} ${styles.fontSize} ${styles.fontFamily}`;
    const caretOffset = ctx.measureText(currentLine).width;
    ctx.restore();

    const caretX = paddingLeft + caretOffset + fontSize * 0.32;
    const visibleX = Math.max(
      paddingLeft + 18,
      Math.min(fieldRect.width - paddingRight - 18, caretX),
    );

    return {
      x: Math.max(0, Math.min(width, fieldRect.left - canvasRect.left + visibleX)),
      y: Math.max(0, Math.min(height, fieldRect.bottom - canvasRect.top + 14)),
    };
  }

  function getTypingFieldAnchor() {
    const field = getActiveThresholdField();
    const canvasRect = canvas.getBoundingClientRect();
    const fieldRect = field?.getBoundingClientRect?.();

    if (!fieldRect) {
      return { x: width * 0.5, y: height * 0.6, width: width * 0.42 };
    }

    return {
      x: Math.max(0, Math.min(width, fieldRect.left - canvasRect.left + fieldRect.width * 0.5)),
      y: Math.max(0, Math.min(height, fieldRect.bottom - canvasRect.top + 18)),
      width: Math.max(1, Math.min(width, fieldRect.width)),
    };
  }

  function addTypingSparks(amount, mode = 'character') {
    const isSpace = mode === 'space';
    const count = Math.round(isSpace ? 8 + amount * 5 : 3 + amount * 3);
    const spread = isSpace ? Math.min(180, typing.spaceWidth * 0.38) : 34;

    for (let index = 0; index < count; index += 1) {
      const angle = isSpace
        ? -Math.PI * (0.2 + Math.random() * 0.6)
        : -Math.PI * (0.22 + Math.random() * 0.58);
      const speed = (isSpace ? 0.68 : 0.45) + Math.random() * 0.85 + amount * 0.18;
      sparks.push({
        x: (isSpace ? typing.spaceX : typing.x) + (Math.random() - 0.5) * spread,
        y: (isSpace ? typing.spaceY : typing.y) + (Math.random() - 0.5) * (isSpace ? 18 : 12),
        vx: Math.cos(angle) * speed + (Math.random() - 0.5) * (isSpace ? 0.65 : 0.35),
        vy: Math.sin(angle) * speed - (isSpace ? 0.34 : 0.18),
        life: 1,
        decay: (isSpace ? 0.018 : 0.026) + Math.random() * 0.018,
        size: (isSpace ? 1.2 : 0.9) + Math.random() * (isSpace ? 2.1 : 1.8),
        phase: Math.random() * Math.PI * 2,
        color: colors[Math.floor(Math.random() * colors.length)],
      });
    }

    if (sparks.length > 48) {
      sparks = sparks.slice(sparks.length - 48);
    }
  }

  function pulseFromTyping(strength = 1, mode = 'character') {
    if (reduceMotion.matches) {
      resize();
      draw(performance.now());
      return;
    }

    const focus = getTypingFocus();
    const fieldAnchor = getTypingFieldAnchor();
    const amount = Math.max(0.45, Math.min(1.75, strength));
    const isSpace = mode === 'space';
    typing.active = true;
    typing.x = focus.x;
    typing.y = focus.y;
    typing.spaceX = fieldAnchor.x;
    typing.spaceY = fieldAnchor.y;
    typing.spaceWidth = fieldAnchor.width;
    typing.energy = Math.min(1.8, typing.energy + (isSpace ? 0.72 : 0.48) * amount);
    typing.ring = Math.min(1, typing.ring + (isSpace ? 0.52 : 0.26) * amount);
    typing.spaceEnergy = Math.min(1.9, typing.spaceEnergy + (isSpace ? 1.05 : 0.12) * amount);
    typing.spaceWave = Math.min(1, typing.spaceWave + (isSpace ? 0.72 : 0.08) * amount);
    typing.burstUntil = performance.now() + (isSpace ? 760 : 560);
    addTypingSparks(amount, mode);

    for (const p of particles) {
      const sourceX = isSpace ? typing.spaceX : typing.x;
      const sourceY = isSpace ? typing.spaceY : typing.y;
      const radius = isSpace ? 306 : 218;
      const dx = p.x - sourceX;
      const dy = p.y - sourceY;
      const distance = Math.hypot(dx, dy);
      if (distance <= 0 || distance >= radius) continue;

      const force = Math.pow(1 - distance / radius, 2) * amount;
      if (isSpace) {
        const direction = dx === 0 ? (Math.random() > 0.5 ? 1 : -1) : dx / Math.abs(dx);
        p.vx += direction * force * 1.35 + (-dy / distance) * force * 0.22;
        p.vy += (dy / distance) * force * 0.36 - force * 0.24;
      } else {
        p.vx += (dx / distance) * force * 0.9 + (-dy / distance) * force * 0.28;
        p.vy += (dy / distance) * force * 0.7 + (dx / distance) * force * 0.22;
      }
    }

    if (!raf) {
      last = 0;
      raf = requestAnimationFrame(frame);
    }
  }

  function bindTypingReaction() {
    const fields = getThresholdFields();
    if (!fields.length) return;

    typing.lastValueLength = fields.reduce((total, field) => total + field.value.length, 0);
    let spaceQueued = false;

    fields.forEach((field) => {
      field.addEventListener('focus', () => {
        pulseFromTyping(0.55);
      });

      field.addEventListener('keydown', (event) => {
        spaceQueued = event.code === 'Space' && !event.metaKey && !event.ctrlKey && !event.altKey;
      });

      field.addEventListener('input', (event) => {
        const nextLength = fields.reduce((total, nextField) => total + nextField.value.length, 0);
        const delta = Math.abs(nextLength - typing.lastValueLength);
        const selectionIndex = typeof field.selectionStart === 'number' ? field.selectionStart : field.value.length;
        const insertedSpace =
          (typeof InputEvent !== 'undefined' && event instanceof InputEvent && event.inputType === 'insertText' && event.data === ' ') ||
          (spaceQueued && field.value.charAt(Math.max(0, selectionIndex - 1)) === ' ');
        typing.lastValueLength = nextLength;
        spaceQueued = false;
        pulseFromTyping(delta || 1, insertedSpace ? 'space' : 'character');
      });
    });
  }

  function update(now) {
    const dt = last ? Math.min(2.2, (now - last) / 16.67) : 1;
    last = now;

    const t = now * 0.001;
    const currentColors = getThemeColors();
    const focusX = width * 0.5;
    const focusY = height * 0.52;
    const typingLive = typing.energy > 0.015 || typing.spaceEnergy > 0.015 || now < typing.burstUntil;

    if (typingLive) {
      typing.energy *= Math.pow(0.885, dt);
      typing.ring *= Math.pow(0.9, dt);
      typing.spaceEnergy *= Math.pow(0.865, dt);
      typing.spaceWave *= Math.pow(0.88, dt);
    } else {
      typing.active = false;
      typing.energy = 0;
      typing.ring = 0;
      typing.spaceEnergy = 0;
      typing.spaceWave = 0;
    }

    sparks = sparks
      .map((spark) => {
        spark.life -= spark.decay * dt;
        spark.x += spark.vx * dt;
        spark.y += spark.vy * dt;
        spark.vx *= Math.pow(0.95, dt);
        spark.vy *= Math.pow(0.96, dt);
        spark.vy -= 0.006 * dt;
        return spark;
      })
      .filter((spark) => spark.life > 0);

    for (const p of particles) {
      const targetX = p.homeX + Math.sin(t * p.speed + p.phase) * p.orbit;
      const targetY = p.homeY + Math.cos(t * p.speed * 0.72 + p.phase) * p.orbit * 0.44;

      p.vx += (targetX - p.x) * 0.003 * dt; // Slower return to orbit
      p.vy += (targetY - p.y) * 0.003 * dt;

      p.vx += (focusX - p.x) * 0.0002 * dt;
      p.vy += (focusY - p.y) * 0.00015 * dt;

      if (pointer.active) {
        const dx = p.x - pointer.x;
        const dy = p.y - pointer.y;
        const distance = Math.hypot(dx, dy);

        if (distance > 0 && distance < 160) {
          const force = Math.pow(1 - distance / 160, 2);
          // Gentle repel
          p.vx += (dx / distance) * force * 0.8 * dt;
          p.vy += (dy / distance) * force * 0.8 * dt;
        }
      }

      if (typing.active && typing.energy > 0.01) {
        const dx = p.x - typing.x;
        const dy = p.y - typing.y;
        const distance = Math.hypot(dx, dy);

        if (distance > 0 && distance < 224) {
          const force = Math.pow(1 - distance / 224, 2) * typing.energy;
          const swirl = 0.42 + Math.sin(t * 5.2 + p.phase) * 0.18;
          p.vx += (dx / distance) * force * 0.28 * dt;
          p.vy += (dy / distance) * force * 0.22 * dt;
          p.vx += (-dy / distance) * force * swirl * dt;
          p.vy += (dx / distance) * force * swirl * 0.78 * dt;
        }
      }

      if (typing.active && typing.spaceEnergy > 0.01) {
        const dx = p.x - typing.spaceX;
        const dy = p.y - typing.spaceY;
        const xRadius = Math.max(96, typing.spaceWidth * 0.54);
        const yRadius = 156;
        const distance = Math.hypot(dx / xRadius, dy / yRadius);

        if (distance > 0 && distance < 1.28) {
          const force = Math.pow(1 - distance / 1.28, 2) * typing.spaceEnergy;
          const direction = dx === 0 ? 0 : dx / Math.abs(dx);
          p.vx += direction * force * 0.42 * dt;
          p.vy += (-0.2 + (dy / yRadius) * 0.16) * force * dt;
        }
      }

      p.vx *= Math.pow(0.94, dt); // Less friction for smoother glide
      p.vy *= Math.pow(0.94, dt);
      p.x += p.vx * dt;
      p.y += p.vy * dt;
    }
  }

  function draw(now) {
    ctx.clearRect(0, 0, width, height);

    const currentColors = getThemeColors();
    const linkLimit = Math.max(86, Math.min(126, width * 0.16));
    ctx.lineWidth = 0.9;

    for (let i = 0; i < particles.length; i += 1) {
      for (let j = i + 1; j < particles.length; j += 1) {
        const a = particles[i];
        const b = particles[j];
        const distance = Math.hypot(a.x - b.x, a.y - b.y);
        if (distance > linkLimit) continue;

        const opacity = Math.pow(1 - distance / linkLimit, 2) * 0.12; // Softer links
        
        // Gradient link for ethereal feel
        const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
        grad.addColorStop(0, `rgba(${currentColors[a.colorIndex]}, ${opacity})`);
        grad.addColorStop(1, `rgba(${currentColors[b.colorIndex]}, ${opacity})`);
        
        ctx.strokeStyle = grad;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }

    if (typing.active && typing.energy > 0.02) {
      const radius = 40 + typing.ring * 90 + Math.sin(now * 0.004) * 3;
      const opacity = Math.min(0.4, typing.energy * 0.18);
      const gradient = ctx.createRadialGradient(typing.x, typing.y, 6, typing.x, typing.y, radius);
      gradient.addColorStop(0, `rgba(255,255,255,${opacity * 0.8})`);
      gradient.addColorStop(0.3, `rgba(158,139,255,${opacity})`);
      gradient.addColorStop(1, 'rgba(158,139,255,0)');

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(typing.x, typing.y, radius, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = `rgba(158,139,255,${opacity * 0.6})`;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(typing.x, typing.y, radius * 0.55, 0, Math.PI * 2);
      ctx.stroke();
      ctx.lineWidth = 0.9;
    }

    if (typing.active && typing.spaceEnergy > 0.02) {
      const opacity = Math.min(0.28, typing.spaceEnergy * 0.16);
      const waveWidth = Math.min(typing.spaceWidth * 0.74, width * 0.68) * (0.55 + typing.spaceWave * 0.45);
      const waveAmp = 2.5 + typing.spaceEnergy * 3.2;
      const waveY = typing.spaceY + 3;

      ctx.save();
      ctx.strokeStyle = `rgba(144,103,198,${opacity})`;
      ctx.lineWidth = 1.25;
      ctx.beginPath();
      for (let index = 0; index <= 28; index += 1) {
        const progress = index / 28;
        const x = typing.spaceX - waveWidth * 0.5 + waveWidth * progress;
        const y = waveY + Math.sin(progress * Math.PI * 2 + now * 0.012) * waveAmp;
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      ctx.strokeStyle = `rgba(247,236,225,${opacity * 0.78})`;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.ellipse(
        typing.spaceX,
        typing.spaceY + 1,
        waveWidth * 0.28,
        10 + typing.spaceWave * 15,
        0,
        0,
        Math.PI * 2,
      );
      ctx.stroke();
      ctx.restore();
      ctx.lineWidth = 0.9;
    }

    for (const spark of sparks) {
      const drift = Math.sin(now * 0.008 + spark.phase) * 1.8;
      const opacity = Math.max(0, spark.life) * 0.62;

      ctx.fillStyle = `rgba(${spark.color}, ${opacity})`;
      ctx.beginPath();
      ctx.arc(spark.x + drift, spark.y, spark.size * (0.7 + spark.life * 0.45), 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(247,236,225,${opacity * 0.72})`;
      ctx.beginPath();
      ctx.arc(spark.x + drift - 0.3, spark.y - 0.4, Math.max(0.42, spark.size * 0.36), 0, Math.PI * 2);
      ctx.fill();
    }

    for (const p of particles) {
      const pulse = 0.8 + Math.sin(now * 0.0015 + p.phase) * 0.25;
      const glowOpacity = 0.8;

      // Outer glow
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * pulse * 3.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${currentColors[p.colorIndex]}, ${glowOpacity * 0.15})`;
      ctx.fill();

      // Inner core
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * pulse, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${currentColors[p.colorIndex]}, ${glowOpacity})`;
      ctx.fill();

      // Bright center
      ctx.fillStyle = 'rgba(255,255,255,0.9)';
      ctx.beginPath();
      ctx.arc(p.x - p.r * 0.15, p.y - p.r * 0.15, Math.max(0.6, p.r * 0.35), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function frame(now) {
    resize();

    if (reduceMotion.matches) {
      typing.active = false;
      typing.energy = 0;
      typing.ring = 0;
      typing.spaceEnergy = 0;
      typing.spaceWave = 0;
      sparks = [];
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
  bindTypingReaction();
  raf = requestAnimationFrame(frame);
}

mountIntroParticles();
