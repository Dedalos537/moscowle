import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type GameKind = 'platformer' | 'reflex' | 'simulation' | 'jclic' | 'clic3' | 'flash' | 'html';
export type KpiKey = 'accuracy' | 'avg_time' | 'completion' | 'errors' | 'collected';
export type LevelId = 'inicial' | 'en_proceso' | 'logrado' | 'destacado';

/** Umbrales de cada indicador: tres cortes que separan los cuatro niveles. */
export type KpiProfile = Partial<Record<KpiKey, [number, number, number]>>;

export interface CatalogGame {
  id: number;
  title: string;
  filename: string;
  kind: GameKind;
  kind_label: string;
  area: string | null;
  ages: string | null;
  description: string | null;
  thumbnail: string | null;
  is_active: boolean;
  play_url: string;
  // Solo para el equipo:
  kpis?: KpiProfile;
  kpis_custom?: boolean;
  available?: boolean;
  source?: string | null;
}

export interface KpiSpec {
  key: KpiKey;
  label: string;
  unit: string;
  better: 'high' | 'low';
}

export interface LevelSpec {
  id: LevelId;
  label: string;
}

export interface CatalogResponse {
  success: boolean;
  games: CatalogGame[];
  kpi_catalog?: KpiSpec[];
  levels?: LevelSpec[];
  kinds?: Record<GameKind, string>;
}

export interface KpiReading {
  key: KpiKey;
  label: string;
  unit: string;
  value: number;
  level: LevelId;
  level_index: number;
  thresholds: number[];
  trend: -1 | 0 | 1 | null;
}

export interface PatientLevel {
  patient_id: number;
  patient: string;
  plays: number;
  plays_week?: number;
  level: LevelId | null;
  level_index: number | null;
  kpis: KpiReading[];
  last_played: string | null;
}

export interface GameLevelsResponse {
  success: boolean;
  game: CatalogGame;
  patients: PatientLevel[];
  distribution: Record<LevelId, number>;
  levels: LevelSpec[];
}

export interface GameResult {
  game_name: string;
  game_id?: number | null;
  session_id?: number | null;
  accuracy?: number;
  avg_time?: number;
  level_reached?: number | null;
  deaths?: number | null;
  coins?: number | null;
  score?: number | null;
  duration_s?: number;
  kpis?: Partial<Record<'completion' | 'errors' | 'collected', number>>;
}

/** Catálogo de juegos (todos los roles) y niveles de KPI (solo el equipo). */
@Injectable({ providedIn: 'root' })
export class GameCatalogService {
  private http = inject(HttpClient);

  /** Los juegos viven en el dominio de la API (también cuando la app se sirve desde cPanel). */
  readonly gamesOrigin = new URL(environment.apiBaseUrl || window.location.origin, window.location.origin).origin;

  playUrl(game: CatalogGame, extra: Record<string, string | number | null | undefined> = {}): string {
    const url = new URL(game.play_url, this.gamesOrigin);
    url.searchParams.set('game_id', String(game.id));
    url.searchParams.set('title', game.title);
    for (const [k, v] of Object.entries(extra)) if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, String(v));
    return url.toString();
  }

  catalog(): Observable<CatalogResponse> {
    return this.http.get<CatalogResponse>('/api/games/catalog');
  }

  update(id: number, patch: Partial<Pick<CatalogGame, 'title' | 'description' | 'area' | 'ages' | 'is_active' | 'kind'>> & { kpis?: KpiProfile | null }): Observable<{ success: boolean; game: CatalogGame; error?: string }> {
    return this.http.patch<{ success: boolean; game: CatalogGame; error?: string }>(`/api/games/${id}`, patch);
  }

  remove(id: number): Observable<{ success: boolean; archived: boolean; plays?: number }> {
    return this.http.delete<{ success: boolean; archived: boolean; plays?: number }>(`/api/games/${id}`);
  }

  upload(file: File, title: string): Observable<{ status: string; game?: { id: number; title: string }; error?: string; activities?: number; warnings?: string[] }> {
    const form = new FormData();
    form.append('file', file);
    form.append('name', title);
    form.append('title', title);
    return this.http.post<{ status: string; game?: { id: number; title: string }; error?: string; activities?: number; warnings?: string[] }>('/api/games/upload', form);
  }

  levels(id: number): Observable<GameLevelsResponse> {
    return this.http.get<GameLevelsResponse>(`/api/games/${id}/levels`);
  }

  patientLevels(patientId: number): Observable<{ success: boolean; games: (PatientLevel & { game: CatalogGame })[]; levels: LevelSpec[] }> {
    return this.http.get<{ success: boolean; games: (PatientLevel & { game: CatalogGame })[]; levels: LevelSpec[] }>(`/api/games/levels/patient/${patientId}`);
  }

  saveResult(result: GameResult): Observable<{ status: string }> {
    return this.http.post<{ status: string }>('/api/save_game', result);
  }
}
