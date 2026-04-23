#* MCP-Stats-Oracle Plumber API
#*
#* Persistent R worker serving 7 statistical analysis tools over HTTP.
#* Started once, reused across many MCP calls — eliminates R startup overhead.
#*
#* Launch (from project root):
#*   Rscript -e "plumber::pr_run(plumber::pr('r_scripts/plumber_server.R'), port=8787)"
#*
#* Plumber sets the working directory to this file's directory, so the tool
#* scripts are sourced with plain filenames.

`%||%` <- function(a, b) if (!is.null(a)) a else b

source("describe_tool.R")
source("catch22_tool.R")
source("changepoint_tool.R")
source("mrcd_tool.R")
source("mfi_tool.R")
source("tsrepr_tool.R")
source("nowcast_tool.R")
source("plot_tool.R")

SAFE_DOWNSAMPLE_MAX <- 5000L
STRICT_MAX <- 10000L

downsample_uniform <- function(x) {
  if (length(x) > SAFE_DOWNSAMPLE_MAX) {
    idx <- round(seq(1, length(x), length.out = SAFE_DOWNSAMPLE_MAX))
    return(x[idx])
  }
  x
}

ensure_len <- function(name, x, hard_max = STRICT_MAX) {
  if (length(x) > hard_max) {
    stop(sprintf(
      "%s: input has %d points; max is %d (downsampling would alias output).",
      name, length(x), hard_max
    ))
  }
  x
}

wrap <- function(expr) {
  result <- withCallingHandlers(
    tryCatch(expr, error = function(e) list(error = conditionMessage(e))),
    warning = function(w) invokeRestart("muffleWarning")
  )
  if (is.list(result) && !is.null(result$error)) {
    return(list(error = as.character(result$error)))
  }
  result
}

#* Health check
#* @get /health
#* @serializer unboxedJSON
function() list(status = "ok", tools = 8L, version = "0.2.0")

#* Describe a numeric series
#* @post /describe
#* @serializer unboxedJSON
function(req) {
  body <- jsonlite::fromJSON(req$postBody, simplifyVector = TRUE)
  wrap(run_describe(downsample_uniform(body$data)))
}

#* Catch22 time series features
#* @post /catch22
#* @serializer unboxedJSON
function(req) {
  body <- jsonlite::fromJSON(req$postBody, simplifyVector = TRUE)
  wrap(run_catch22(downsample_uniform(body$data)))
}

#* Bayesian changepoint detection
#* @post /changepoint
#* @serializer unboxedJSON
function(req) {
  body <- jsonlite::fromJSON(req$postBody, simplifyVector = TRUE)
  hazard <- body$hazard_rate %||% 250
  wrap(run_changepoint(ensure_len("changepoint", body$data), hazard_rate = as.integer(hazard)))
}

#* MRCD robust-regression outlier detection
#* @post /mrcd
#* @serializer unboxedJSON
function(req) {
  body <- jsonlite::fromJSON(req$postBody, simplifyVector = FALSE)
  cols <- lapply(body$data, function(col) as.numeric(unlist(col)))
  data <- as.data.frame(cols)
  target <- body$target
  predictors <- unlist(body$predictors)
  wrap(run_mrcd(data = ensure_len("mrcd", data), target = target, predictors = predictors))
}

#* Money Flow Index
#* @post /mfi
#* @serializer unboxedJSON
function(req) {
  body <- jsonlite::fromJSON(req$postBody, simplifyVector = TRUE)
  window <- body$window %||% 14L
  wrap(run_mfi(
    ensure_len("mfi.high", body$high),
    ensure_len("mfi.low", body$low),
    ensure_len("mfi.close", body$close),
    ensure_len("mfi.volume", body$volume),
    window = as.integer(window)
  ))
}

#* TSrepr feature-clipping compression
#* @post /tsrepr
#* @serializer unboxedJSON
function(req) {
  body <- jsonlite::fromJSON(req$postBody, simplifyVector = TRUE)
  wrap(run_tsrepr(ensure_len("tsrepr", body$data, hard_max = 1024L)))
}

#* Bayesian nowcast
#* @post /nowcast
#* @serializer unboxedJSON
function(req) {
  body <- jsonlite::fromJSON(req$postBody, simplifyVector = FALSE)
  hist <- as.numeric(unlist(body$historical))
  signals <- if (!is.null(body$signals)) body$signals else list()
  doq <- if (!is.null(body$day_of_quarter)) as.integer(body$day_of_quarter) else NA_integer_
  wrap(run_nowcast(historical = hist, signals = signals, day_of_quarter = doq))
}

#* Terminal-rendered ggplot (line / histogram / scatter)
#* @post /plot
#* @serializer unboxedJSON
function(req) {
  body <- jsonlite::fromJSON(req$postBody, simplifyVector = TRUE)
  plot_type <- body$plot_type %||% "line"
  data <- if (!is.null(body$data)) as.numeric(body$data) else NULL
  x    <- if (!is.null(body$x))    as.numeric(body$x)    else NULL
  y    <- if (!is.null(body$y))    as.numeric(body$y)    else NULL
  title <- body$title %||% ""
  bins  <- as.integer(body$bins %||% 30L)
  width  <- as.integer(body$width  %||% 70L)
  height <- as.integer(body$height %||% 16L)
  if (!is.null(data)) data <- ensure_len(sprintf("plot(%s).data", plot_type), data)
  if (!is.null(x))    x    <- ensure_len("plot(scatter).x", x)
  if (!is.null(y))    y    <- ensure_len("plot(scatter).y", y)
  wrap(run_plot(
    plot_type = plot_type,
    data = data, x = x, y = y,
    title = title, bins = bins,
    width = width, height = height
  ))
}
