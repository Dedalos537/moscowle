// DCE — Diego Centeno Estuvo Acá
export interface AdminAPIToken {
  id: number;
  created_at: string;
  is_active: boolean;
}

export interface CreateTokenResponse {
  token: string;
  id: number;
  created_at: string;
  is_active: boolean;
}
