/**
 * Viewer service - wrapper around That Open Company components.
 * Provides a clean API for the Vue components to interact with the 3D viewer.
 */

export interface ViewerConfig {
  container: HTMLDivElement;
}

// The actual viewer logic is co-located in IfcViewer.vue
// This file can be extended for shared viewer utilities

export function formatCoordinate(value: number): string {
  return value.toFixed(3);
}

export function formatDistance(meters: number): string {
  if (meters < 1) return `${(meters * 1000).toFixed(0)} mm`;
  if (meters < 1000) return `${meters.toFixed(2)} m`;
  return `${(meters / 1000).toFixed(2)} km`;
}

export function formatArea(sqMeters: number): string {
  return `${sqMeters.toFixed(2)} m²`;
}

export function formatVolume(cubicMeters: number): string {
  return `${cubicMeters.toFixed(3)} m³`;
}
