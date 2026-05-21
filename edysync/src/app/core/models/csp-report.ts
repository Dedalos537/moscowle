// DCE — Diego Centeno Estuvo Acá
export interface CSPReport {
  id: number;
  received_at: string;
  document_uri: string;
  violated_directive: string;
  blocked_uri: string;
  original_policy?: string;
  ip_address?: string;
  user_id?: number;
}

export interface CSPReportFilter {
  directive: string;
  blocked_uri: string;
  since: string;
  page?: number;
  per_page?: number;
}

export interface CSPReportResponse {
  items: CSPReport[];
  page: number;
  per_page: number;
  total: number;
  pages: number;
}
