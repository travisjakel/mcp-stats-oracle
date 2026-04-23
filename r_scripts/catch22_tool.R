#' Catch22 Time Series Features
#'
#' Compute the 22 canonical time series features (CAnonical Time-series CHaracteristics)
#' covering distribution, autocorrelation, nonlinear dynamics, and spectral properties.
#'
#' @param data numeric vector (typically 50–5000 points)
#' @return list with `features` (named list of 22 features) and `interpretation` (string)

run_catch22 <- function(data) {
  if (!requireNamespace("Rcatch22", quietly = TRUE)) {
    stop("Rcatch22 package required")
  }

  x <- as.numeric(data)
  x <- x[is.finite(x)]

  if (length(x) < 10) {
    return(list(
      error = "Need at least 10 finite data points",
      n = length(x)
    ))
  }

  res <- Rcatch22::catch22_all(x, catch24 = FALSE)
  feats <- setNames(as.list(res$values), res$names)

  ac1   <- feats[["CO_f1ecac"]]
  trend <- feats[["SB_BinaryStats_mean_longstretch1"]]
  dist  <- feats[["DN_HistogramMode_5"]]
  nonlin <- feats[["CO_trev_1_num"]]

  parts <- character()
  if (!is.na(ac1)) {
    if (ac1 > 5) parts <- c(parts, sprintf("strong autocorrelation (f1ecac=%.2f) suggesting persistence/trending", ac1))
    else if (ac1 < 1.5) parts <- c(parts, sprintf("rapid decorrelation (f1ecac=%.2f) suggesting near-white-noise dynamics", ac1))
  }
  if (!is.na(trend)) {
    if (trend > 0.2) parts <- c(parts, sprintf("long positive runs (longstretch=%.2f) indicating regime persistence", trend))
  }
  if (!is.na(nonlin)) {
    if (abs(nonlin) > 0.1) parts <- c(parts, sprintf("significant time-reversal asymmetry (trev=%.2f) — nonlinear dynamics present", nonlin))
  }

  interpretation <- if (length(parts) == 0) {
    "Series appears roughly stationary with no dominant linear or nonlinear structure."
  } else {
    paste0("Series shows ", paste(parts, collapse = "; "), ".")
  }

  list(
    n = length(x),
    features = feats,
    interpretation = interpretation
  )
}
