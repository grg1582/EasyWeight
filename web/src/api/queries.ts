// What each page loads, with TanStack Query: it caches answers, shows the
// cached one at once when you come back to a page, and refetches in the
// background.

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type {
  Device,
  DeviceCreated,
  PairingStatus,
  Stats,
  User,
  WorkoutDetail,
  WorkoutPage,
} from "./types";

export const PAGE_SIZE = 20;

export function useMe(enabled: boolean) {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/users/me"),
    enabled,
    retry: false,
    staleTime: Infinity,
    refetchInterval: false,
  });
}

export function useStats(days: number) {
  return useQuery({
    queryKey: ["stats", days],
    queryFn: () => api<Stats>(`/stats?days=${days}`),
  });
}

export function useWorkouts(page: number, deviceId?: string, limit = PAGE_SIZE) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(page * limit) });
  if (deviceId) params.set("device_id", deviceId);
  return useQuery({
    queryKey: ["workouts", { page, deviceId, limit }],
    queryFn: () => api<WorkoutPage>(`/workouts?${params}`),
    placeholderData: keepPreviousData, // keep the old page on screen while the next loads
  });
}

export function useWorkout(id: string) {
  return useQuery({
    queryKey: ["workout", id],
    queryFn: () => api<WorkoutDetail>(`/workouts/${id}`),
  });
}

export function useDevices() {
  return useQuery({ queryKey: ["devices"], queryFn: () => api<Device[]>("/devices") });
}

export function useAddDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api<DeviceCreated>("/devices", { method: "POST", json: { name } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });
}

/** Connect the mirror showing this code (from its QR code) to your account */
export function useClaimPairing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ code, name }: { code: string; name: string }) =>
      api<PairingStatus>(`/pairing/${encodeURIComponent(code)}/claim`, {
        method: "POST",
        json: { name: name.trim() || null },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });
}

export function useRemoveDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/devices/${id}`, { method: "DELETE" }),
    // Its workouts are gone too
    onSuccess: () => queryClient.invalidateQueries(),
  });
}
