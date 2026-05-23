import textwrap
import json

from music_disc_maker.classes import BuiltDisc

def generate_disc_registry_js(discs: list[BuiltDisc]) -> str:
    """Generate the JavaScript registry consumed by the jukebox behavior script."""
    registry_entries = []

    for disc in discs:
        registry_entries.append([
            disc.item_id,
            {
                "soundId": disc.sound_id,
                "title": disc.title,
                "durationTicks": disc.duration_ticks,
                "volume": 1.0,
                "pitch": 1.0,
            },
        ])

    return textwrap.dedent(f"""
        export const DISC_REGISTRY = new Map({json.dumps(registry_entries, indent=2, ensure_ascii=False)});

        export const CUSTOM_DISC_IDS = new Set(Array.from(DISC_REGISTRY.keys()));
    """).strip() + "\n"


def generate_main_js() -> str:
    """Generate the deterministic jukebox playback manager script."""
    return textwrap.dedent("""
        import { EquipmentSlot, ItemStack, system, world } from "@minecraft/server";
        import { CUSTOM_DISC_IDS, DISC_REGISTRY } from "./disc_registry.js";

        const STATE_PROPERTY = "custom_discs:active_jukeboxes";
        const RECONCILE_INTERVAL_TICKS = 20;
        const activeJukeboxes = new Map();

        system.run(initializePlaybackManager);
        system.runInterval(reconcileActiveJukeboxes, RECONCILE_INTERVAL_TICKS);

        world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
          try {
            if (event.isFirstEvent === false) {
              return;
            }

            const block = event.block;

            if (!block || block.typeId !== "minecraft:jukebox") {
              return;
            }

            const key = getBlockKey(block);
            const active = activeJukeboxes.get(key);
            const storedRecord = getStoredRecord(block);

            if (active || isCustomDisc(storedRecord)) {
              event.cancel = true;
              const storedItemTypeId = storedRecord ? storedRecord.typeId : undefined;
              system.run(() => ejectCustomDisc(block, key, storedItemTypeId));
              return;
            }

            if (storedRecord) {
              return;
            }

            const itemStack = event.itemStack;

            if (!itemStack) {
              return;
            }

            const disc = DISC_REGISTRY.get(itemStack.typeId);

            if (!disc) {
              return;
            }

            event.cancel = true;

            const player = event.player;
            const itemTypeId = itemStack.typeId;

            system.run(() => playCustomDisc(player, block, itemTypeId, disc));
          } catch (error) {
            console.warn(`[custom_discs] Jukebox before-event failed: ${error}`);
          }
        });

        world.afterEvents.playerBreakBlock.subscribe((event) => {
          try {
            const key = getEventKey(event);

            if (!activeJukeboxes.has(key)) {
              return;
            }

            cleanupDestroyedJukebox(key, event.dimension, getBlockLocation(event.block), "player_break");
          } catch (error) {
            console.warn(`[custom_discs] playerBreakBlock cleanup failed: ${error}`);
          }
        });

        if (world.afterEvents.blockExplode) {
          world.afterEvents.blockExplode.subscribe((event) => {
            try {
              const key = getEventKey(event);

              if (!activeJukeboxes.has(key)) {
                return;
              }

              cleanupDestroyedJukebox(key, event.dimension, getBlockLocation(event.block), "block_explode");
            } catch (error) {
              console.warn(`[custom_discs] blockExplode cleanup failed: ${error}`);
            }
          });
        }

        function initializePlaybackManager() {
          const states = loadPersistedStates();
          let changed = false;

          for (const state of states) {
            try {
              const dimension = getDimensionById(state.dimensionId);

              if (!dimension) {
                changed = true;
                continue;
              }

              if (state.playing) {
                stopPersistedSound(dimension, state.soundId);
                state.playing = false;
                state.soundInstance = undefined;
                state.timeoutId = undefined;
                changed = true;
              }

              const block = getBlockForState(state);

              if (!block || block.typeId !== "minecraft:jukebox") {
                changed = true;
                continue;
              }

              const storedRecord = getStoredRecord(block);

              if (!isExpectedCustomDisc(storedRecord, state.itemTypeId)) {
                changed = true;
                continue;
              }

              activeJukeboxes.set(state.key, state);
            } catch (error) {
              console.warn(`[custom_discs] Failed to hydrate jukebox state: ${error}`);
              changed = true;
            }
          }

          if (changed) {
            persistActiveStates();
          }
        }

        function playCustomDisc(player, block, itemTypeId, disc) {
          let consumedFromPlayer = false;
          let storedByJukebox = false;

          try {
            const recordPlayer = block.getComponent("minecraft:record_player");

            if (!recordPlayer) {
              return;
            }

            const existingRecord = getStoredRecord(block);

            if (existingRecord) {
              return;
            }

            consumedFromPlayer = takeOneFromMainhand(player, itemTypeId);

            if (!consumedFromPlayer && !isCreativePlayer(player)) {
              return;
            }

            try {
              recordPlayer.setRecord(itemTypeId, false);
              storedByJukebox = true;
            } catch (error) {
              console.warn(`[custom_discs] Jukebox refused to store ${itemTypeId}: ${error}`);
            }

            let soundInstance;

            try {
              soundInstance = block.dimension.playSound(disc.soundId, getBlockCenter(block), {
                volume: disc.volume,
                pitch: disc.pitch,
              });
            } catch (error) {
              console.warn(`[custom_discs] Failed to play ${disc.soundId}: ${error}`);
              recoverDiscAfterFailedPlay(block, itemTypeId, storedByJukebox, consumedFromPlayer);
              return;
            }

            const key = getBlockKey(block);
            const startTick = system.currentTick;
            const state = {
              version: 1,
              key,
              dimensionId: block.dimension.id,
              x: block.x,
              y: block.y,
              z: block.z,
              itemTypeId,
              soundId: disc.soundId,
              title: disc.title,
              durationTicks: disc.durationTicks,
              startTick,
              endTick: startTick + disc.durationTicks,
              playing: true,
              storedByJukebox,
              consumedFromPlayer,
              soundInstance,
              timeoutId: undefined,
            };

            activeJukeboxes.set(key, state);
            scheduleFinish(state);
            persistActiveStates();
          } catch (error) {
            console.warn(`[custom_discs] Failed to play custom disc: ${error}`);
            recoverDiscAfterFailedPlay(block, itemTypeId, storedByJukebox, consumedFromPlayer);
          }
        }

        function ejectCustomDisc(block, key, storedItemTypeId) {
          const active = activeJukeboxes.get(key);
          const itemTypeId = storedItemTypeId || (active ? active.itemTypeId : undefined);

          try {
            if (active) {
              clearStateTimeout(active);
              stopStateSound(block.dimension, active);
            }

            const recordPlayer = block.getComponent("minecraft:record_player");

            if (recordPlayer && storedItemTypeId) {
              try {
                recordPlayer.ejectRecord();
                activeJukeboxes.delete(key);
                persistActiveStates();
                return;
              } catch (error) {
                console.warn(`[custom_discs] Failed to eject stored record: ${error}`);
              }
            }

            if (recordPlayer && active && active.storedByJukebox) {
              try {
                recordPlayer.ejectRecord();
                activeJukeboxes.delete(key);
                persistActiveStates();
                return;
              } catch (error) {
                console.warn(`[custom_discs] Failed to eject active record: ${error}`);
              }
            }

            if (itemTypeId) {
              spawnDiscItem(block.dimension, getBlockCenter(block), itemTypeId);
            }
          } catch (error) {
            console.warn(`[custom_discs] Failed to eject custom disc: ${error}`);
          } finally {
            activeJukeboxes.delete(key);
            persistActiveStates();
          }
        }

        function finishCustomDisc(key) {
          const active = activeJukeboxes.get(key);

          if (!active) {
            return;
          }

          try {
            const dimension = getDimensionById(active.dimensionId);

            if (dimension) {
              stopStateSound(dimension, active);
            }
          } catch (error) {
            console.warn(`[custom_discs] Failed to finish ${active.soundId}: ${error}`);
          }

          active.playing = false;
          active.soundInstance = undefined;
          active.timeoutId = undefined;

          activeJukeboxes.set(key, active);
          persistActiveStates();
        }

        function reconcileActiveJukeboxes() {
          let changed = false;

          for (const [key, state] of Array.from(activeJukeboxes.entries())) {
            try {
              if (state.playing && system.currentTick >= state.endTick) {
                finishCustomDisc(key);
                changed = true;
                continue;
              }

              const block = getBlockForState(state);

              if (!block) {
                continue;
              }

              if (block.typeId !== "minecraft:jukebox") {
                cleanupDestroyedJukebox(key, block.dimension, {
                  x: state.x,
                  y: state.y,
                  z: state.z,
                }, "reconcile_missing_jukebox");
                changed = true;
                continue;
              }

              const storedRecord = getStoredRecord(block);

              if (state.storedByJukebox && !isExpectedCustomDisc(storedRecord, state.itemTypeId)) {
                stopStateSound(block.dimension, state);
                clearStateTimeout(state);
                activeJukeboxes.delete(key);
                changed = true;
                continue;
              }

              if (!state.storedByJukebox && !state.playing) {
                activeJukeboxes.delete(key);
                changed = true;
              }
            } catch (error) {
              console.warn(`[custom_discs] Reconcile failed for ${key}: ${error}`);
            }
          }

          if (changed) {
            persistActiveStates();
          }
        }

        function cleanupDestroyedJukebox(key, dimension, location, reason) {
          const active = activeJukeboxes.get(key);

          if (!active) {
            return;
          }

          try {
            clearStateTimeout(active);
            stopStateSound(dimension, active);

            if (!active.storedByJukebox && active.consumedFromPlayer) {
              spawnDiscItem(dimension, {
                x: location.x + 0.5,
                y: location.y + 0.5,
                z: location.z + 0.5,
              }, active.itemTypeId);
            }

            console.warn(`[custom_discs] Cleaned up custom jukebox at ${key}: ${reason}`);
          } catch (error) {
            console.warn(`[custom_discs] Destroy cleanup failed for ${key}: ${error}`);
          } finally {
            activeJukeboxes.delete(key);
            persistActiveStates();
          }
        }

        function recoverDiscAfterFailedPlay(block, itemTypeId, storedByJukebox, consumedFromPlayer) {
          try {
            const recordPlayer = block.getComponent("minecraft:record_player");

            if (recordPlayer && storedByJukebox) {
              recordPlayer.ejectRecord();
              return;
            }

            if (consumedFromPlayer) {
              spawnDiscItem(block.dimension, getBlockCenter(block), itemTypeId);
            }
          } catch (error) {
            console.warn(`[custom_discs] Failed to recover disc after play failure: ${error}`);
          }
        }

        function scheduleFinish(state) {
          clearStateTimeout(state);
          const remainingTicks = Math.max(1, state.endTick - system.currentTick);
          state.timeoutId = system.runTimeout(() => finishCustomDisc(state.key), remainingTicks);
        }

        function clearStateTimeout(state) {
          if (state && state.timeoutId !== undefined) {
            try {
              system.clearRun(state.timeoutId);
            } catch {
            }

            state.timeoutId = undefined;
          }
        }

        function stopStateSound(dimension, state) {
          if (!state || !state.soundId) {
            return;
          }

          if (state.soundInstance && typeof state.soundInstance.stop === "function") {
            try {
              state.soundInstance.stop();
              return;
            } catch (error) {
              console.warn(`[custom_discs] SoundInstance.stop failed for ${state.soundId}: ${error}`);
            }
          }

          stopPersistedSound(dimension, state.soundId);
        }

        function stopPersistedSound(dimension, soundId) {
          try {
            if (dimension && typeof dimension.stopSound === "function") {
              dimension.stopSound(soundId);
            }
          } catch (error) {
            console.warn(`[custom_discs] dimension.stopSound failed for ${soundId}: ${error}`);
          }
        }

        function takeOneFromMainhand(player, itemTypeId) {
          if (isCreativePlayer(player)) {
            return false;
          }

          const equippable = player.getComponent("minecraft:equippable");

          if (!equippable) {
            return false;
          }

          const heldItem = equippable.getEquipment(EquipmentSlot.Mainhand);

          if (!heldItem || heldItem.typeId !== itemTypeId) {
            return false;
          }

          if (heldItem.amount <= 1) {
            return equippable.setEquipment(EquipmentSlot.Mainhand, undefined);
          }

          const nextItem = heldItem.clone();
          nextItem.amount -= 1;

          return equippable.setEquipment(EquipmentSlot.Mainhand, nextItem);
        }

        function spawnDiscItem(dimension, location, itemTypeId) {
          try {
            dimension.spawnItem(new ItemStack(itemTypeId, 1), {
              x: location.x,
              y: location.y + 0.5,
              z: location.z,
            });
          } catch (error) {
            console.warn(`[custom_discs] Failed to spawn ${itemTypeId}: ${error}`);
          }
        }

        function loadPersistedStates() {
          const raw = world.getDynamicProperty(STATE_PROPERTY);

          if (raw === undefined) {
            return [];
          }

          if (typeof raw !== "string") {
            world.setDynamicProperty(STATE_PROPERTY, undefined);
            return [];
          }

          try {
            const parsed = JSON.parse(raw);

            if (!Array.isArray(parsed)) {
              return [];
            }

            return parsed.map(normalizePersistedState).filter(Boolean);
          } catch (error) {
            console.warn(`[custom_discs] Failed to parse ${STATE_PROPERTY}: ${error}`);
            world.setDynamicProperty(STATE_PROPERTY, undefined);
            return [];
          }
        }

        function normalizePersistedState(value) {
          if (!value || typeof value !== "object") {
            return undefined;
          }

          if (
            typeof value.key !== "string" ||
            typeof value.dimensionId !== "string" ||
            typeof value.x !== "number" ||
            typeof value.y !== "number" ||
            typeof value.z !== "number" ||
            typeof value.itemTypeId !== "string" ||
            typeof value.soundId !== "string"
          ) {
            return undefined;
          }

          return {
            version: 1,
            key: value.key,
            dimensionId: value.dimensionId,
            x: value.x,
            y: value.y,
            z: value.z,
            itemTypeId: value.itemTypeId,
            soundId: value.soundId,
            title: typeof value.title === "string" ? value.title : value.itemTypeId,
            durationTicks: typeof value.durationTicks === "number" ? value.durationTicks : 1,
            startTick: typeof value.startTick === "number" ? value.startTick : system.currentTick,
            endTick: typeof value.endTick === "number" ? value.endTick : system.currentTick,
            playing: Boolean(value.playing),
            storedByJukebox: Boolean(value.storedByJukebox),
            consumedFromPlayer: Boolean(value.consumedFromPlayer),
            soundInstance: undefined,
            timeoutId: undefined,
          };
        }

        function persistActiveStates() {
          const states = Array.from(activeJukeboxes.values()).map(serializeState);

          if (states.length === 0) {
            world.setDynamicProperty(STATE_PROPERTY, undefined);
            return;
          }

          world.setDynamicProperty(STATE_PROPERTY, JSON.stringify(states));
        }

        function serializeState(state) {
          return {
            version: 1,
            key: state.key,
            dimensionId: state.dimensionId,
            x: state.x,
            y: state.y,
            z: state.z,
            itemTypeId: state.itemTypeId,
            soundId: state.soundId,
            title: state.title,
            durationTicks: state.durationTicks,
            startTick: state.startTick,
            endTick: state.endTick,
            playing: state.playing,
            storedByJukebox: state.storedByJukebox,
            consumedFromPlayer: state.consumedFromPlayer,
          };
        }

        function getStoredRecord(block) {
          try {
            const recordPlayer = block.getComponent("minecraft:record_player");

            if (!recordPlayer) {
              return undefined;
            }

            return recordPlayer.getRecord();
          } catch {
            return undefined;
          }
        }

        function isCustomDisc(itemStack) {
          return Boolean(itemStack && CUSTOM_DISC_IDS.has(itemStack.typeId));
        }

        function isExpectedCustomDisc(itemStack, itemTypeId) {
          return Boolean(itemStack && itemStack.typeId === itemTypeId && CUSTOM_DISC_IDS.has(itemStack.typeId));
        }

        function isCreativePlayer(player) {
          try {
            const gameMode = player.getGameMode();
            return gameMode === "Creative" || gameMode === "creative";
          } catch {
            return false;
          }
        }

        function getBlockForState(state) {
          const dimension = getDimensionById(state.dimensionId);

          if (!dimension) {
            return undefined;
          }

          try {
            return dimension.getBlock({
              x: state.x,
              y: state.y,
              z: state.z,
            });
          } catch {
            return undefined;
          }
        }

        function getDimensionById(dimensionId) {
          const candidates = [
            dimensionId,
            dimensionId.replace("minecraft:", ""),
          ];

          for (const candidate of candidates) {
            try {
              return world.getDimension(candidate);
            } catch {
            }
          }

          return undefined;
        }

        function getBlockCenter(block) {
          if (typeof block.center === "function") {
            return block.center();
          }

          return {
            x: block.x + 0.5,
            y: block.y + 0.5,
            z: block.z + 0.5,
          };
        }

        function getBlockLocation(block) {
          return {
            x: block.x,
            y: block.y,
            z: block.z,
          };
        }

        function getBlockKey(block) {
          return `${block.dimension.id}:${block.x}:${block.y}:${block.z}`;
        }

        function getEventKey(event) {
          return `${event.dimension.id}:${event.block.x}:${event.block.y}:${event.block.z}`;
        }
    """).strip() + "\n"
