-- Per-player toggle for the doge-speak toasts (the comrade narrates your factory in
-- broken doge grammar). Cosmetic only; default on.
data:extend({
  {
    type = "bool-setting",
    name = "commie-doge-toasts",
    setting_type = "runtime-per-user",
    default_value = true,
    order = "commie-doge-a",
  },
})
