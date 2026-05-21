// DCE — Diego Centeno Estuvo Acá
export interface AITrainingStatus {
  model_exists: boolean;
  training_in_progress: boolean;
}

export interface TrainResponse {
  started: boolean;
}
