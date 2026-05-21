// DCE — Diego Centeno Estuvo Acá
export interface YapeTransaction {
  id: number;
  operation_number: string;
  transaction_date: string;
  sender_name: string;
  amount: number;
  message?: string;
  category?: string;
  is_expense: boolean;
  expense_id?: number;
  receipt_image_path?: string;
  import_batch_id?: number;
}

export interface YapeImportStats {
  total: number;
  imported: number;
  errors: number;
}

export interface YapeDashboardStats {
  total: number;
  pending: number;
}
