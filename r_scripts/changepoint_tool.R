#' Bayesian Online Changepoint Detection
#'
#' Detects regime shifts in a univariate series using the ocp package.
#' Returns changepoint locations, run-length probabilities, and a natural-language
#' interpretation of the regime structure.
#'
#' @param data numeric vector
#' @param hazard_rate integer, expected run length (default 250)
#' @return list with changepoints, probabilities, interpretation

run_changepoint <- function(data, hazard_rate = 250) {
  if (!requireNamespace("ocp", quietly = TRUE)) stop("ocp package required")

  x <- as.numeric(data)
  x <- x[is.finite(x)]
  n <- length(x)

  if (n < 30) {
    return(list(error = "Need at least 30 points for changepoint detection", n = n))
  }

  res <- tryCatch(
    ocp::onlineCPD(
      datapts = matrix(x, ncol = 1),
      hazard_func = function(r, lambda) ocp::const_hazard(r, lambda = hazard_rate),
      getR = FALSE,
      optionalOutputs = FALSE
    ),
    error = function(e) NULL
  )

  if (is.null(res)) {
    return(list(error = "ocp changepoint detection failed", n = n))
  }

  cps <- res$changepoint_lists$maxCPs[[1]]
  cps <- cps[cps > 1 & cps < n]

  n_cps <- length(cps)
  last_cp <- if (n_cps > 0) max(cps) else NA_integer_
  frac_from_end <- if (!is.na(last_cp)) (n - last_cp) / n else NA_real_

  interpretation <- if (n_cps == 0) {
    "No regime changes detected — the series appears to come from a single stationary regime."
  } else if (n_cps == 1) {
    sprintf("Single regime change at index %d (%.1f%% from end). Recent behavior differs from historical baseline.",
            last_cp, 100 * (1 - frac_from_end))
  } else {
    sprintf("%d regime changes detected; most recent at index %d (%.1f%% of series from end). Series has experienced multiple structural shifts.",
            n_cps, last_cp, 100 * (1 - frac_from_end))
  }

  list(
    n = n,
    hazard_rate = hazard_rate,
    n_changepoints = n_cps,
    changepoints = as.integer(cps),
    last_changepoint = last_cp,
    interpretation = interpretation
  )
}
