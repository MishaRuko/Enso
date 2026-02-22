// --- User Preferences ---

export interface UserPreferences {
  style: string;
  budget_min: number;
  budget_max: number;
  currency: string;
  colors: string[];
  room_type: string;
  lifestyle: string[];
  must_haves: string[];
  dealbreakers: string[];
  existing_furniture: string[];
}

// --- Room Data ---

export interface DoorWindow {
  wall: "north" | "south" | "east" | "west";
  position_m: number;
  width_m: number;
}

export interface RoomData {
  name: string;
  width_m: number;
  length_m: number;
  height_m: number;
  x_offset_m: number;
  z_offset_m: number;
  doors: DoorWindow[];
  windows: DoorWindow[];
  shape: string;
  area_sqm: number;
}

export interface FloorplanAnalysis {
  rooms: RoomData[];
}

// --- Furniture ---

export interface FurnitureDimensions {
  width_cm: number;
  depth_cm: number;
  height_cm: number;
}

export interface FurnitureItem {
  id: string;
  retailer: string;
  name: string;
  price: number;
  currency: string;
  dimensions: FurnitureDimensions | null;
  image_url: string;
  product_url: string;
  glb_url: string;
  category: string;
  selected: boolean;
}

// --- Placement ---

export interface Position3D {
  x: number;
  y: number;
  z: number;
}

export interface FurniturePlacement {
  item_id: string;
  name: string;
  position: Position3D;
  rotation_y_degrees: number;
  reasoning: string;
}

export interface PlacementResult {
  placements: FurniturePlacement[];
}

// --- Session ---

export interface DesignSession {
  id: string;
  created_at: string;
  updated_at: string;
  status:
    | "pending"
    | "consulting"
    | "analyzing_floorplan"
    | "floorplan_ready"
    | "floorplan_failed"
    | "searching"
    | "furniture_found"
    | "searching_failed"
    | "sourcing"
    | "sourcing_failed"
    | "placing"
    | "placing_failed"
    | "placement_ready"
    | "complete"
    | "checkout";
  client_name: string | null;
  client_email: string | null;
  preferences: UserPreferences;
  floorplan_url: string | null;
  room_data: FloorplanAnalysis | null;
  room_glb_url: string | null;
  furniture_list: FurnitureItem[];
  placements: PlacementResult | null;
  total_price: number | null;
  payment_link: string | null;
  payment_status: string;
  miro_board_url: string | null;
  demo_selected: boolean;
}

// --- Pipeline ---

export interface DesignJob {
  id: string;
  session_id: string;
  created_at: string;
  completed_at: string | null;
  status: "pending" | "running" | "completed" | "failed";
  phase: string;
  trace: TraceEvent[];
  result: Record<string, unknown> | null;
}

export interface TraceEvent {
  step: string;
  message: string;
  timestamp?: number;
  duration_ms?: number;
  image_url?: string;
  input_image?: string;
  input_images?: string[];
  output_image?: string;
  input_prompt?: string;
  output_text?: string;
  model?: string;
  error?: string;
  data?: Record<string, unknown>;
}
