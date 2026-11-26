// The shapes the backend sends. They mirror backend/easyweight_api/schemas.py

export type Exercise = "curl" | "raise" | "press" | "squat" | "pushup";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface User {
  id: string;
  email: string;
  created_at: string;
  is_demo: boolean;
}

export interface Device {
  id: string;
  name: string;
  /** "browser" holds the workouts done with the camera on the Train page */
  kind: "mirror" | "browser";
  created_at: string;
  last_seen_at: string | null;
}

export interface DeviceCreated extends Device {
  token: string;
}

/** A mirror connected by scanning its QR code */
export interface PairingStatus {
  status: "waiting" | "paired";
  device: Device | null;
  expires_at: string;
}

export interface WorkoutSummary {
  id: string;
  device_id: string;
  started_at: string;
  ended_at: string | null;
  total_sets: number;
  total_reps: number;
  exercises: Exercise[];
}

export interface WorkoutSet {
  id: string;
  exercise: Exercise;
  set_number: number;
  reps: number;
  started_at: string;
  ended_at: string | null;
}

export interface WorkoutDetail extends WorkoutSummary {
  sets: WorkoutSet[];
}

export interface WorkoutPage {
  items: WorkoutSummary[];
  total: number;
}

export interface Stats {
  days: number;
  workouts: number;
  per_exercise: { exercise: Exercise; sets: number; reps: number }[];
  per_day: { date: string; reps: number }[];
}
