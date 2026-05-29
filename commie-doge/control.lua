-- Comrade Doge: doge-speak toasts.
--
-- Pure cosmetic flavor. Every toast is a *local* flying text (LuaPlayer.create_local_flying_text)
-- shown only to the relevant player, and the script never mutates game state -- so it cannot
-- affect balance and cannot desync (local flying text is client-side and unsaved). Frequent
-- events are gated by a per-player cooldown plus a random chance so the comrade quips
-- spontaneously instead of spamming; rare/important events bypass the cooldown.

local COLOR     = { r = 1.0, g = 0.86, b = 0.32 }  -- comrade gold
local COOLDOWN  = 150     -- min ticks between cooldown-gated toasts for one player
local THREAT_R  = 32      -- tiles: "enemy nearby" alert radius

-- Broken-doge x Soviet grammar, one pool per category. Glory to labor, wow.
local LINES = {
  research         = { "much science. very five-year-plan. glory to labor. wow.",
                       "such research. the Party approve. comrade smart.",
                       "knowledge for the proletariat. very progress. wow." },
  research_started = { "the Party set new goal. such plan begins. wow.",
                       "much ambition. for the five-year-plan. comrade study." },
  rocket           = { "such rocket. to space for the motherland. wow.",
                       "the cosmos belong to the workers now. very glory.",
                       "comrade doge reach orbit. for the Union. wow." },
  died             = { "comrade fall for the cause. very brave. such martyr.",
                       "doge join the eternal collective. wow. so sad.",
                       "much death. the revolution continue. respawn soon." },
  respawn          = { "comrade return to the struggle. very alive. back to labor.",
                       "such revival. the Party still need you. wow." },
  hurt             = { "much hurt. the bourgeoisie strike. defend!",
                       "ow. very pain. for the workers, endure.",
                       "such ouch. report to the medical commissar." },
  biters           = { "class enemy approach! such teeth. defend the collective!",
                       "many counter-revolutionary bug. very alert.",
                       "the bourgeoisie send their dogs. grr. for the motherland!" },
  mined            = { "much mine. seize the means of production. wow.",
                       "such dig. resource for the people. very labor.",
                       "ore for the collective. dig dig comrade." },
  built            = { "such build. fulfill the five-year-plan. wow.",
                       "much construct. for the glory of the Union.",
                       "factory for the proletariat. comrade proud." },
  crafted          = { "much craft. labor is glory. wow.",
                       "such handiwork. the workers united. very make." },
  kill             = { "class enemy defeated! such victory. wow.",
                       "counter-revolutionary squashed. for the people!",
                       "the bourgeoisie fall. many bug down. very triumph." },
  drive            = { "such vehicle. property of the collective. vroom!",
                       "much drive. comrade go zoom for the motherland." },
  night            = { "such dark. the long night of struggle. wow.",
                       "much night. the vanguard never sleep. brr." },
  morning          = { "red sun rise over the motherland. much labor await. wow.",
                       "dawn of new workday. very glory. comrade rise." },
  joined           = { "comrade join the collective! welcome. wow.",
                       "new worker for the Union. very solidarity." },
  capsule          = { "such boom. for the people! wow.",
                       "much grenade. strike the bourgeoisie. very kaboom." },
  tile             = { "land reclaimed for the motherland. very territory. wow.",
                       "such terraform. expand the Union. comrade build." },
  armor            = { "new armor. comrade ready for the struggle. wow.",
                       "such protection. defend the revolution." },
  repair           = { "such fix. maintain the means of production. wow.",
                       "much repair. the collective endure." },
  dropped          = { "comrade share. from each according to ability. wow.",
                       "such generous. for the common good." },
}

local function toasts_on(player)
  local s = settings.get_player_settings(player)["commie-doge-toasts"]
  return (s == nil) or s.value   -- default on if the setting is somehow absent
end

-- Show a doge-speak line above a player's character. Respects the per-player cooldown unless
-- `bypass` is set (used for rare events). Returns true if it actually spoke.
local function say(player, category, bypass)
  if not (player and player.valid and player.connected) then return false end
  local char = player.character
  if not (char and char.valid) then return false end
  if not toasts_on(player) then return false end

  storage.last = storage.last or {}
  local now = game.tick
  local last = storage.last[player.index]
  if not bypass and last and (now - last) < COOLDOWN then return false end

  local pool = LINES[category]
  if not pool then return false end
  storage.last[player.index] = now
  player.create_local_flying_text{
    text = pool[math.random(#pool)],
    position = { char.position.x, char.position.y - 2.2 },
    color = COLOR,
    time_to_live = 220,
    speed = 0.45,
  }
  return true
end

local function say_all(category)
  for _, player in pairs(game.connected_players) do
    say(player, category, true)   -- global events are rare; bypass the cooldown
  end
end

-- A cooldown-gated event toast that only fires `chance` of the time, so high-frequency
-- actions (mining, building, crafting) read as occasional spontaneous quips.
local function maybe(player, category, chance)
  if math.random() <= chance then say(player, category, false) end
end

local function player_from(event)
  return event.player_index and game.get_player(event.player_index) or nil
end

-- ---- rare / important events (bypass cooldown) ------------------------------------------
script.on_event(defines.events.on_research_finished, function() say_all("research") end)
script.on_event(defines.events.on_rocket_launched,   function() say_all("rocket")   end)
script.on_event(defines.events.on_player_died,       function(e) say(game.get_player(e.player_index), "died", true) end)
script.on_event(defines.events.on_player_respawned,  function(e) say(game.get_player(e.player_index), "respawn", true) end)

script.on_event(defines.events.on_player_driving_changed_state, function(e)
  local p = game.get_player(e.player_index)
  if p and p.driving then say(p, "drive", false) end
end)

-- ---- frequent events (cooldown + random chance) -----------------------------------------
script.on_event(defines.events.on_player_mined_entity,  function(e) maybe(player_from(e), "mined",   0.10) end)
script.on_event(defines.events.on_player_crafted_item,  function(e) maybe(player_from(e), "crafted", 0.08) end)
script.on_event(defines.events.on_built_entity,         function(e) maybe(player_from(e), "built",   0.14) end)

-- enemy unit killed by a player's character -> a victory bork (filtered to units for UPS)
script.on_event(defines.events.on_entity_died, function(e)
  local cause = e.cause
  if cause and cause.valid and cause.type == "character" and cause.player then
    maybe(cause.player, "kill", 0.18)
  end
end, {{ filter = "type", type = "unit" }})

-- ---- polled, edge-triggered states (low HP, nearby enemies, day/night) -------------------
script.on_nth_tick(53, function()
  storage.lowhp  = storage.lowhp  or {}
  storage.threat = storage.threat or {}
  storage.night  = storage.night  or {}
  for _, player in pairs(game.connected_players) do
    local char = player.character
    if char and char.valid then
      local i = player.index

      -- hurt: edge-trigger when health crosses below 40%
      local hr = char.get_health_ratio()
      local low = hr ~= nil and hr < 0.40
      if low and not storage.lowhp[i] then say(player, "hurt", false) end
      storage.lowhp[i] = low

      -- threat: edge-trigger when an enemy first comes within range
      local near = char.surface.count_entities_filtered{
        position = char.position, radius = THREAT_R, force = "enemy", limit = 1 } > 0
      if near and not storage.threat[i] then say(player, "biters", false) end
      storage.threat[i] = near

      -- day/night: edge-trigger on the darkness crossing (per surface)
      local si = char.surface.index
      local dark = char.surface.darkness > 0.5
      local was = storage.night[si]
      if was ~= nil and dark ~= was then say(player, dark and "night" or "morning", false) end
      storage.night[si] = dark
    end
  end
end)
