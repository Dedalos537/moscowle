import {
  Component,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnDestroy,
  ChangeDetectionStrategy,
} from '@angular/core';

type Obstacle = { x: number; w: number; h: number };

const DINO_MAP = [
  '......###...........',
  '.....#####..........',
  '....#######.........',
  '....#########.......',
  '...###########......',
  '...##############...',
  '..#################.',
  '..########.########.',
  '.########..########.',
  '.########..########.',
  '.########..########.',
  '.########..########.',
  '..########.#######..',
  '..########.#######..',
  '...######..######...',
  '...######..######...',
  '...######..######...',
  '...######..#####....',
  '...######..#####....',
  '...#..#....#..#.....',
  '...#..#....#..#.....',
];

@Component({
  selector: 'app-server-down-game',
  standalone: true,
  imports: [],
  templateUrl: './server-down-game.html',
  styleUrl: './server-down-game.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServerDownGame implements AfterViewInit, OnDestroy {
  @ViewChild('gameCanvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  private readonly W = 480;
  private readonly H = 170;
  private readonly GROUND = 138;
  private readonly GRAVITY = 0.55;
  private readonly JUMP_V = -12;
  private readonly CELL = 2;

  private get dark() {
    return typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
  }
  private get ink() {
    return this.dark ? '#e2e2e2' : '#1a1a1a';
  }
  private get accent() {
    return this.dark ? '#a5d087' : '#4a7c37';
  }
  private get cloudFill() {
    return this.dark ? '#3a3b3c' : '#e3ded6';
  }
  private get nightTint() {
    return this.dark ? 'rgba(255,255,255,0.05)' : 'rgba(26,26,26,0.07)';
  }
  private get overFill() {
    return this.dark ? 'rgba(24,25,26,0.88)' : 'rgba(245,240,235,0.88)';
  }

  private ctx!: CanvasRenderingContext2D;
  private raf = 0;
  private last = 0;
  private speed = 6;
  private score = 0;
  private high = 0;
  private frame = 0;
  private over = false;
  private groundOffset = 0;
  private night = false;

  private dino = {
    x: 56,
    y: this.GROUND - DINO_MAP.length * 2,
    w: DINO_MAP[0].length * 2,
    h: DINO_MAP.length * 2,
    vy: 0,
    grounded: true,
  };
  private obstacles: Obstacle[] = [];
  private spawnGap = 40;
  private clouds: { x: number; y: number; s: number }[] = [];
  private stars: { x: number; y: number; s: number }[] = [];

  private onKey = (e: KeyboardEvent) => {
    if (e.code === 'Space' || e.code === 'ArrowUp') {
      e.preventDefault();
      this.action();
    }
  };

  private onPointer = (e: Event) => {
    e.preventDefault();
    this.action();
  };

  ngAfterViewInit(): void {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = this.W * dpr;
    canvas.height = this.H * dpr;
    ctx.scale(dpr, dpr);
    this.ctx = ctx;

    for (let i = 0; i < 3; i++) {
      this.clouds.push({ x: Math.random() * this.W, y: 18 + Math.random() * 28, s: 0.8 + Math.random() * 0.5 });
    }
    for (let i = 0; i < 22; i++) {
      this.stars.push({ x: Math.random() * this.W, y: 10 + Math.random() * 90, s: 1 + Math.random() * 1.5 });
    }

    window.addEventListener('keydown', this.onKey);
    canvas.addEventListener('pointerdown', this.onPointer);

    this.last = performance.now();
    this.raf = requestAnimationFrame(this.loop);
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.raf);
    window.removeEventListener('keydown', this.onKey);
    if (this.canvasRef?.nativeElement) {
      this.canvasRef.nativeElement.removeEventListener('pointerdown', this.onPointer);
    }
  }

  private action() {
    if (this.over) {
      this.reset();
      return;
    }
    if (this.dino.grounded) {
      this.dino.vy = this.JUMP_V;
      this.dino.grounded = false;
    }
  }

  private reset() {
    this.obstacles = [];
    this.speed = 6;
    this.score = 0;
    this.over = false;
    this.dino.y = this.GROUND - this.dino.h;
    this.dino.vy = 0;
    this.dino.grounded = true;
    this.spawnGap = 40;
  }

  private loop = (t: number) => {
    const dt = Math.min((t - this.last) / 16.667, 3);
    this.last = t;
    this.update(dt);
    this.draw();
    this.raf = requestAnimationFrame(this.loop);
  };

  private update(dt: number) {
    if (this.over) return;

    this.frame++;
    this.speed = Math.min(this.speed + 0.0015 * dt, 13);
    this.score += 0.02 * this.speed * dt;
    this.night = Math.floor(this.score / 350) % 2 === 1;

    this.dino.vy += this.GRAVITY * dt;
    this.dino.y += this.dino.vy * dt;
    if (this.dino.y >= this.GROUND - this.dino.h) {
      this.dino.y = this.GROUND - this.dino.h;
      this.dino.vy = 0;
      this.dino.grounded = true;
    }

    this.groundOffset = (this.groundOffset + this.speed * dt) % 27;

    for (const c of this.clouds) {
      c.x -= this.speed * 0.15 * dt;
      if (c.x < -60) c.x = this.W + 60;
    }

    this.spawnGap -= dt;
    const lastObs = this.obstacles[this.obstacles.length - 1];
    if (this.spawnGap <= 0 && (!lastObs || lastObs.x < this.W * 0.6)) {
      this.spawnObstacle();
      this.spawnGap = 60 + Math.random() * 80 + (13 - this.speed) * 4;
    }

    for (const o of this.obstacles) {
      o.x -= this.speed * dt;
    }
    this.obstacles = this.obstacles.filter(o => o.x + o.w > -20);

    const d = this.dino;
    const pad = 5;
    for (const o of this.obstacles) {
      const oTop = this.GROUND - o.h + 4;
      if (
        d.x + d.w - pad > o.x &&
        d.x + pad < o.x + o.w &&
        d.y + d.h > oTop + 2 &&
        d.y + pad < this.GROUND
      ) {
        this.over = true;
        this.high = Math.max(this.high, Math.floor(this.score));
        break;
      }
    }
  }

  private spawnObstacle() {
    const r = Math.random();
    const x = this.W + 10;
    if (r < 0.45) {
      this.obstacles.push({ x, w: 14, h: 18 });
    } else if (r < 0.8) {
      this.obstacles.push({ x, w: 18, h: 30 });
    } else {
      this.obstacles.push({ x, w: 14, h: 18 }, { x: x + 30, w: 14, h: 16 });
    }
  }

  private draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.W, this.H);

    if (this.night) {
      ctx.fillStyle = this.nightTint;
      ctx.fillRect(0, 0, this.W, this.GROUND);
      ctx.fillStyle = this.ink;
      ctx.globalAlpha = 0.55;
      for (const s of this.stars) {
        ctx.fillRect(s.x, s.y, s.s, s.s);
      }
      ctx.globalAlpha = 1;
      ctx.strokeStyle = this.ink;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(this.W - 44, 26, 12, 0, Math.PI * 2);
      ctx.stroke();
    } else {
      ctx.fillStyle = this.cloudFill;
      for (const c of this.clouds) {
        this.cloud(c.x, c.y, c.s);
      }
    }

    ctx.fillStyle = this.ink;
    ctx.globalAlpha = 0.75;
    for (let x = -27; x < this.W; x += 27) {
      ctx.fillRect(x - this.groundOffset, this.GROUND, 15, 2);
    }
    ctx.globalAlpha = 1;

    ctx.fillStyle = this.ink;
    for (const o of this.obstacles) {
      this.cactus(o);
    }

    this.dinoSprite();

    ctx.fillStyle = this.accent;
    ctx.font = '700 11px Inter, system-ui, sans-serif';
    ctx.textAlign = 'right';
    const s = Math.floor(this.score);
    ctx.fillText(`HI ${String(this.high).padStart(5, '0')}  ${String(s).padStart(5, '0')}`, this.W - 8, 16);

    if (this.over) {
      ctx.fillStyle = this.overFill;
      ctx.fillRect(0, 0, this.W, this.H);
      ctx.fillStyle = this.ink;
      ctx.font = '800 13px Inter, system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('GAME OVER', this.W / 2, this.H / 2 - 4);
      ctx.fillStyle = this.accent;
      ctx.font = '600 10px Inter, system-ui, sans-serif';
      ctx.fillText('Toca o pulsa ESPACIO para reintentar', this.W / 2, this.H / 2 + 14);
    }
  }

  private cloud(x: number, y: number, s: number) {
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.arc(x, y, 8 * s, 0, Math.PI * 2);
    ctx.arc(x + 11 * s, y - 4 * s, 9 * s, 0, Math.PI * 2);
    ctx.arc(x + 23 * s, y, 7 * s, 0, Math.PI * 2);
    ctx.fill();
  }

  private cactus(o: Obstacle) {
    const ctx = this.ctx;
    const base = this.GROUND;
    const armW = Math.max(2, Math.round(o.w * 0.4));
    const armH = Math.max(6, Math.round(o.h * 0.45));
    ctx.fillRect(o.x, base - o.h, o.w, o.h);
    ctx.fillRect(o.x + o.w, base - o.h + armH - 2, armW, armH);
    ctx.fillRect(o.x - armW, base - o.h + Math.round(o.h * 0.5), armW, armH - 4);
  }

  private dinoSprite() {
    const ctx = this.ctx;
    const cell = this.CELL;
    const map = DINO_MAP;
    const bob = this.over ? 0 : Math.floor(this.frame / 5) % 2 === 0 ? 0 : -2;
    const y = this.dino.y + bob;
    ctx.fillStyle = this.accent;
    for (let r = 0; r < map.length; r++) {
      const row = map[r];
      for (let c = 0; c < row.length; c++) {
        if (row[c] === '#') {
          ctx.fillRect(this.dino.x + c * cell, y + r * cell, cell, cell);
        }
      }
    }
    ctx.fillStyle = this.dark ? '#18191a' : '#ffffff';
    ctx.fillRect(this.dino.x + 9 * cell, y + 3 * cell, cell * 2, cell * 2);
  }
}
