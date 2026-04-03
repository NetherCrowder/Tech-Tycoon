import pandas as pd
from datetime import datetime
import math
import random
import uuid
from back.models.assets import CATALOG

class GameState:
    def __init__(self):
        # Datos del jugador y servidor
        self.game_name = "Offline"
        self.nickname = "Unknown"
        self.difficulty = "facil"
        self.start_time = None
        self.is_active = False
        self.nivel_mundo = 1

        # Recursos y Métricas Core
        self.creditos = 0.0
        self.energia = 100
        self.energia_max = 100
        self.amenaza = 0.0  # Porcentaje (0.0 a 100.0)
        self.amenaza_rate = 1.0 # Incremento por tick base
        self.oleada = 0
        
        # INVENTARIO
        self.inventory = {asset_id: 0 for asset_id in CATALOG.keys()}
        
        # TEMPORIZADORES DE ESTADO
        self.timers = {asset_id: {"active": 0.0, "cooldown": 0.0} for asset_id in CATALOG.keys() if CATALOG[asset_id].type == "generator"}
        
        # SISTEMA DE COMBATE
        self.active_enemies = []
        self.active_defenses = []
        self._wave_active = False # Flag para saber si hay una horda en curso para recompensa

        # RECURSOS ESPECIALES
        self.w_hex = 0
        
        # Sistema de Prestigio
        self.nivel_renacer = 0
        self.puntos_prestigio = 0

        # DataFrame para historial o progresión estadística (Pandas)
        self.economia_log = pd.DataFrame(columns=["timestamp", "evento", "monto", "balance_actual"])

    def create_new_game(self, game_name: str, nickname: str, difficulty: str):
        self.game_name = game_name
        self.nickname = nickname
        self.difficulty = difficulty
        self.start_time = datetime.now()
        self.is_active = True
        self.nivel_mundo = 1

        if difficulty == "facil":
            self.creditos = 100.0
            self.amenaza_rate = 0.5
        elif difficulty == "moderada":
            self.creditos = 100.0
            self.amenaza_rate = 1.0
        elif difficulty == "dificil":
            self.creditos = 100.0
            self.amenaza_rate = 2.0
        elif difficulty == "infernal":
            self.creditos = 100.0
            self.amenaza_rate = 3.5

        self.amenaza = 0.0
        self.energia = 100
        self.energia_max = 100
        self.oleada = 1

        self._log_transaction("Inicio_Partida", self.creditos)

    def _spawn_wave(self):
        """Genera los enemigos acorde a la fórmula progresiva acordada."""
        f = self.oleada
        n = self.nivel_mundo
        base = 5
        
        # Formula: round( (Base * n) + (f^1.2 * log(f+1) * n) )
        cantidad = round((base * n) + ((f ** 1.2) * math.log(f + 1) * n))
        
        base_enemy = CATALOG.get("enemy_ghosnet")
        if not base_enemy:
            return
            
        for _ in range(cantidad):
            enemigo = {
                "uuid": str(uuid.uuid4()),
                "asset_id": "enemy_ghosnet",
                "health": base_enemy.health,
                "max_health": base_enemy.health,
                "distance": 100.0,
                "speed": base_enemy.speed,
                "angle": random.randint(0, 359)
            }
            self.active_enemies.append(enemigo)
            
        self._wave_active = True
        self._log_transaction(f"Oleada_{self.oleada}", -cantidad)

    def process_tick(self, delta_secs: float = 1.0):
        if not self.is_active:
            return

        # 1. Procesar Generadores
        upg_cableado = self.inventory.get("upg_cableado", 0)
        upg_vent = self.inventory.get("upg_ventilacion", 0)
        
        # Multiplicador Cableado: 1.05 + 0.44 * (Nivel - 1)
        cableado_mult = 1.0
        if upg_cableado > 0:
            cableado_mult = 1.05 + 0.44 * (upg_cableado - 1)
            
        # Reducción Ventilación %: 10 + 2 * Nivel
        vent_bonus = 0
        if upg_vent > 0:
            vent_bonus = 10 + 2 * upg_vent

        for gen_id, timers in self.timers.items():
            if self.inventory[gen_id] > 0:
                if timers["active"] > 0:
                    base_rate = CATALOG[gen_id].generation_rate
                    rate = base_rate * self.inventory[gen_id] * cableado_mult
                    self.creditos += rate * delta_secs
                    timers["active"] -= delta_secs
                    
                    if timers["active"] <= 0:
                        timers["active"] = 0
                        timers["cooldown"] = CATALOG[gen_id].cooldown
                
                elif timers["cooldown"] > 0:
                    # El tiempo de enfriamiento pasa más rápido según el bono
                    timers["cooldown"] -= delta_secs * (1.0 + (vent_bonus / 100.0))
                    if timers["cooldown"] < 0:
                        timers["cooldown"] = 0
                        
        # 2. Amenaza Pasiva y Detección de Victoria de Ola
        if len(self.active_enemies) == 0:
            # Recompensa W-Hex si acabamos de limpiar la horda
            if self._wave_active:
                self._wave_active = False
                # Formula: W-Hex = round(Base * f^0.7 * log2(n + 1))
                # f = oleada, n = prestigio (base 1)
                f = self.oleada
                n = self.nivel_renacer + 1
                reward = round(5 * (f ** 0.7) * math.log2(n + 1))
                
                self.w_hex += reward
                self._log_transaction(f"VICTORIA_OLA_{self.oleada}", reward)

            self.amenaza += self.amenaza_rate * delta_secs
            if self.amenaza >= 100.0:
                self.amenaza = 0.0
                self._spawn_wave()
                self.oleada += 1

        # 3. Lógica Pasiva Enemiga (Movimiento y I.A. Combate)
        # Iteramos hacia atrás para evitar out-of-index bugs al eliminar
        for i in range(len(self.active_enemies) - 1, -1, -1):
            enemigo = self.active_enemies[i]
            catalog_enemy = CATALOG[enemigo["asset_id"]]
            
            target_distance = 0.0 # Por defecto el núcleo
            
            # Evaluar prioridad: ¿Hay defensas eléctricas activas?
            priorities = catalog_enemy.target_priority or []
            if "defense_electric" in priorities and len(self.active_defenses) > 0 and enemigo["distance"] >= 70.0:
                target_distance = 70.0 # Escala Radial UI
                
            # Desplazamiento
            if enemigo["distance"] > target_distance:
                enemigo["distance"] -= enemigo["speed"] * delta_secs
                # Sujetamos a la raya perimetral si calculamos de más
                if enemigo["distance"] < target_distance:
                    enemigo["distance"] = target_distance
            
            # Combate si hemos llegado a nuestro destino
            if enemigo["distance"] == 70.0 and len(self.active_defenses) > 0:
                # El enemigo aplica DPS a la primera defensa del arreglo
                first_def = self.active_defenses[0]
                first_def["health"] -= catalog_enemy.damage * delta_secs
                
                if first_def["health"] <= 0:
                     # Torre colapsa
                     self.inventory[first_def["asset_id"]] -= 1
                     self.active_defenses.pop(0)
            
            elif enemigo["distance"] <= 0:
                # Llegó al Núcleo y estalla
                self.energia -= catalog_enemy.damage
                self.active_enemies.pop(i)
                
                # Check Death
                if self.energia <= 0:
                    self.energia = 0
                    self.is_active = False # GAME OVER
                    self._log_transaction("GAME_OVER", 0)

        if not self.is_active:
            return

        # 4. Lógica de Defensas (Múltiples ataques independientes)
        # Sincronizamos los arrays de cooldowns por si se compraron nuevas defensas
        if not hasattr(self, "defense_cooldowns"):
            self.defense_cooldowns = {aid: [] for aid, a in CATALOG.items() if a.type == "defense"}
            
        # Bonos de Combate Globales (Tesla y Descarga)
        upg_tesla = self.inventory.get("upg_tesla", 0)
        upg_descarga = self.inventory.get("upg_descarga", 0)
        
        for def_id, count in self.inventory.items():
            asset = CATALOG.get(def_id)
            if asset and asset.type == "defense" and count > 0:
                # 4.1. Calcular Estadísticas Mejoradas
                # Speed Improved % = 10 + 4 * Nivel (Max reduction 50% aprox)
                as_bonus = (10 + 4 * upg_tesla) / 100.0 if upg_tesla > 0 else 0
                effective_as = asset.attack_speed * (1.0 - as_bonus)
                
                # Range Extension % = 15 * Nivel (Max +150%)
                range_bonus = (15 * upg_descarga) / 100.0 if upg_descarga > 0 else 0
                effective_range = asset.range * (1.0 + range_bonus)

                # Asegurar que el array tiene el tamaño del inventario actual
                cd_list = self.defense_cooldowns.setdefault(def_id, [])
                while len(cd_list) < count:
                    cd_list.append(0.0)
                
                # Procesar cada torre independientemente
                for idx in range(count):
                    cd_list[idx] -= delta_secs
                    # Si puede disparar y hay enemigos vivos
                    if cd_list[idx] <= 0 and len(self.active_enemies) > 0:
                        # Seleccionar al más cercano dentro del rango radial (70 es la posición de la torre)
                        # Distancia radial absoluta del enemigo a la torre
                        targets_in_range = [e for e in self.active_enemies if abs(e["distance"] - 70.0) <= effective_range]
                        
                        if targets_in_range:
                            closest = min(targets_in_range, key=lambda e: abs(e["distance"] - 70.0))
                            closest["health"] -= asset.damage
                            
                            if closest["health"] <= 0:
                                self.active_enemies.remove(closest)
                                
                            # Reset de disparo con el AS mejorado
                            cd_list[idx] = effective_as

    def _log_transaction(self, evento: str, monto: float):
        nuevo_log = pd.DataFrame([{
            "timestamp": datetime.now(),
            "evento": evento,
            "monto": monto,
            "balance_actual": self.creditos
        }])
        if self.economia_log.empty:
            self.economia_log = nuevo_log
        else:
            self.economia_log = pd.concat([self.economia_log, nuevo_log], ignore_index=True)

    def get_dict_state(self):
        return {
            "game_name": self.game_name,
            "nickname": self.nickname,
            "difficulty": self.difficulty,
            "is_active": self.is_active,
            "recursos": {
                "creditos": round(self.creditos, 2),
                "w_hex": self.w_hex,
                "energia": self.energia,
                "energia_max": self.energia_max,
                "amenaza": round(self.amenaza, 1),
                "oleada": self.oleada
            },
            "inventory": self.inventory,
            "timers": self.timers,
            "prestigio": {
                "nivel": self.nivel_renacer,
                "puntos": self.puntos_prestigio
            }
        }

game_brain = GameState()

