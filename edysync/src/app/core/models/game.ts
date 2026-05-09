export interface Game {
  id: number;
  title: string;
  filename: string;
  description?: string;
  thumbnail?: string;
  is_active: boolean;
  created_at: string;
}
