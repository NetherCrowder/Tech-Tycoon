import json
import os
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class AssetModel(BaseModel):
    """Modelo modular base para TODAS las entidades del juego cargadas por JSON."""
    id: str
    name: str
    type: str # "generator", "defense", "upgrade", "enemy"
    description: str
    cost: int
    
    # Específico de Generadores
    generation_rate: int = 0
    duration_active: int = 0
    cooldown: int = 0
    
    # Específico de Defensas/Combate
    damage: int = 0
    range: int = 0
    limit: Optional[int] = None # Cantidad máxima de defensas/generadores de este tipo
    combat_type: Optional[str] = None # Ej: "electric", "kinetic"
    attack_speed: float = 0.0 # En segundos
    
    # Específico de Enemigos y Defensas Mortales
    health: int = 0
    max_health: int = 0
    defense: int = 0
    speed: float = 0.0 # Unidades de distancia por segundo
    target_priority: Optional[List[str]] = None # Ej: ["defense_electric", "core"]
    
    # Específico de Mejoras
    cost_type: str = "creditos"
    max_level: Optional[int] = None
    base_multiplier: float = 0.0
    level_step: float = 0.0
    base_reduction: float = 0.0
    base_as: float = 0.0
    affects: Optional[str] = None
    effect_type: Optional[str] = None

# Cargar automáticamente los JSON
CATALOG: Dict[str, AssetModel] = {}

def update_catalog_from_json():
    global CATALOG
    CATALOG.clear()
    
    data_dir = os.path.join("back", "data")
    if not os.path.exists(data_dir):
        return
        
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    for item in items:
                        asset = AssetModel(**item)
                        CATALOG[asset.id] = asset
            except Exception as e:
                print(f"Error cargando {filename}: {e}")

# Ejecutar carga inicial
update_catalog_from_json()

