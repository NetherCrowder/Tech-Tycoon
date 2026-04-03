from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
from contextlib import asynccontextmanager

async def game_tick_loop():
    from back.game_state import game_brain
    while True:
        game_brain.process_tick(1/60)
        await asyncio.sleep(1/60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(game_tick_loop())
    yield
    task.cancel()

app = FastAPI(
    title="Tech Tycoon",
    description="Juego de gestión Tycoon con Tower Defense",
    version="0.1.0",
    lifespan=lifespan
)

# Archivos estáticos en front/static (CSS, JS, imágenes)
app.mount("/static", StaticFiles(directory="front/static"), name="static")


@app.get("/", response_class=FileResponse)
async def main_page():
    """Sirve la página principal del juego."""
    return FileResponse("front/index.html")


@app.get("/game", response_class=FileResponse)
async def game_menu():
    """Menú de inicio de partida: Nueva / Cargar / Regresar."""
    return FileResponse("front/game_menu.html")


from pydantic import BaseModel
from back.game_state import game_brain

class NewGameData(BaseModel):
    game_name: str
    nickname: str
    difficulty: str

@app.get("/new-game", response_class=FileResponse)
async def new_game_page():
    """Formulario para crear nueva partida."""
    return FileResponse("front/new_game.html")

@app.post("/api/game/new")
async def api_create_new_game(data: NewGameData):
    """Recibe los datos del formulario e inicializa el cerebro en Backend."""
    game_brain.create_new_game(data.game_name, data.nickname, data.difficulty)
    print(f"Partida iniciada. Balance Inicial: {game_brain.creditos} ₡")
    return {"status": "success", "message": "Game environment initialized", "state": game_brain.get_dict_state()}

@app.get("/api/game/state")
async def api_get_game_state():
    """Retorna el estado global del juego (Lectura de Frontend)."""
    return game_brain.get_dict_state()

from back.models.assets import CATALOG

@app.get("/api/assets")
async def get_assets():
    """Retorna el catálogo y el estado actual de los assets."""
    return {
        "catalog": {k: v.dict() for k, v in CATALOG.items()},
        "inventory": game_brain.inventory,
        "timers": game_brain.timers,
        "creditos": game_brain.creditos,
        "w_hex": game_brain.w_hex
    }

@app.get("/api/game/map")
async def get_map_state():
    """Retorna los datos posicionales y tácticos para renderizar los mapas."""
    return {
        "defenses": game_brain.active_defenses,
        "enemies": game_brain.active_enemies
    }

class ActionData(BaseModel):
    asset_id: str
    action_type: str # "buy", "activate"

@app.post("/api/action/interact")
async def interact_asset(data: ActionData):
    """Maneja las interacciones: comprar niveles/defensas y activar generadores."""
    if data.asset_id not in CATALOG:
        return {"error": "Invalid asset"}
    
    asset = CATALOG[data.asset_id]
    
    if data.action_type == "buy":
        current_owned = game_brain.inventory[data.asset_id]
        
        # Validar límites (Defensas)
        if asset.limit is not None and current_owned >= asset.limit:
            return {"error": "Límite máximo alcanzado"}
        
        # Validar nivel máximo (Mejoras)
        if asset.type == "upgrade" and hasattr(asset, "max_level") and current_owned >= asset.max_level:
            return {"error": "Nivel máximo de tecnología alcanzado"}

        # Cálculo de Costo Real
        import math
        if getattr(asset, "cost_type", "creditos") == "w_hex":
            # Formula: Costo = Base * log10(n + 1) * Factor^n  (Donde n es el nivel a comprar)
            n = current_owned + 1
            real_cost = round(asset.cost * math.log10(n + 1) * (1.6 ** n))
            
            if game_brain.w_hex >= real_cost:
                game_brain.w_hex -= real_cost
                game_brain.inventory[data.asset_id] += 1
                game_brain._log_transaction(f"Mejora_{data.asset_id}_Nivel_{n}", -real_cost)
                return {"status": "success", "level": game_brain.inventory[data.asset_id], "currency": "w_hex"}
            return {"error": f"W-Hex insuficientes (Necesitas {real_cost})"}
        else:
            # Créditos normales (Nuevas Fórmulas de Balance)
            if asset.type == "generator":
                # Costo_Gen = 100 * 1.15^(n)  (donde n es current_owned)
                real_cost = round(100 * (1.15 ** current_owned))
            elif asset.type == "defense":
                # Costo_Def = 250 * 1.4^(u) (donde u es current_owned)
                real_cost = round(250 * (1.4 ** current_owned))
            else:
                # Otros activos (fallback anterior)
                real_cost = round(asset.cost * (1.5 ** current_owned))
            
            if game_brain.creditos >= real_cost:
                game_brain.creditos -= real_cost
                game_brain.inventory[data.asset_id] += 1
                
                # Instanciar defensa viva si corresponde
                if asset.type == "defense":
                    import uuid
                    import random
                    game_brain.active_defenses.append({
                        "uuid": str(uuid.uuid4()),
                        "asset_id": data.asset_id,
                        "health": asset.health,
                        "max_health": asset.max_health,
                        "cooldown": asset.attack_speed,
                        "angle": random.randint(0, 359)
                    })
                    
                game_brain._log_transaction(f"Comprar_{data.asset_id}", -real_cost)
                return {"status": "success", "level": game_brain.inventory[data.asset_id], "currency": "creditos", "real_cost": real_cost}
            return {"error": "Créditos insuficientes", "real_cost": real_cost}
        
    elif data.action_type == "activate":
        current_owned = game_brain.inventory[data.asset_id]
        if current_owned > 0 and asset.type == "generator":
            timers = game_brain.timers.get(data.asset_id)
            if timers and timers["active"] == 0 and timers["cooldown"] == 0:
                timers["active"] = asset.duration_active
                return {"status": "activated"}
            return {"error": "Generador ocupado o en cooldown"}
        return {"error": "No poseído o no activable"}
    
    return {"error": "Acción desconocida"}

@app.get("/play", response_class=FileResponse)
async def play_game():
    """Interfaz principal del juego (Recursos, Gestión, Mapa)."""
    return FileResponse("front/main_game.html")


@app.get("/maps/level1", response_class=FileResponse)
async def map_level_1():
    """Sirve el mapa independiente (Nivel 1) para cargarlo en el iframe."""
    return FileResponse("front/maps/level1.html")


@app.get("/settings", response_class=FileResponse)
async def settings_page():
    """Página de ajustes del juego."""
    return FileResponse("front/settings.html")


@app.get("/api/status")
async def status():
    """Endpoint de salud de la API."""
    return {"status": "ok", "game": "Tech Tycoon", "version": "0.1.0"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,   # Desactivado: Python 3.14 tiene bugs con multiprocessing spawn + reload
    )
