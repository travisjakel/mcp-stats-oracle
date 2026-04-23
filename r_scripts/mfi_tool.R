#' Money Flow Index
#'
#' Volume-weighted momentum oscillator (0–100). Values above 80 indicate
#' overbought conditions; below 20 oversold.
#'
#' @param high numeric vector of high prices
#' @param low numeric vector of low prices
#' @param close numeric vector of close prices
#' @param volume numeric vector of volumes
#' @param window integer rolling window (default 14)
#' @return list with mfi series, latest value, signal, interpretation

run_mfi <- function(high, low, close, volume, window = 14L) {
  h <- as.numeric(high); l <- as.numeric(low)
  cl <- as.numeric(close); v <- as.numeric(volume)
  n <- length(cl)
  if (length(h) != n || length(l) != n || length(v) != n) {
    stop("high, low, close, volume must be same length")
  }
  if (n < window + 2) {
    return(list(error = sprintf("Need at least %d points (have %d)", window + 2, n), n = n))
  }

  tp <- (h + l + cl) / 3
  rmf <- tp * v

  dtp <- c(NA, diff(tp))
  pos_flow <- ifelse(!is.na(dtp) & dtp > 0, rmf, 0)
  neg_flow <- ifelse(!is.na(dtp) & dtp < 0, rmf, 0)

  pos_sum <- rep(NA_real_, n)
  neg_sum <- rep(NA_real_, n)
  for (i in window:n) {
    idx <- (i - window + 1):i
    pos_sum[i] <- sum(pos_flow[idx], na.rm = TRUE)
    neg_sum[i] <- sum(neg_flow[idx], na.rm = TRUE)
  }

  mfr <- pos_sum / pmax(neg_sum, 1e-12)
  mfi <- 100 - 100 / (1 + mfr)

  latest <- tail(mfi[is.finite(mfi)], 1)
  latest <- if (length(latest)) latest else NA_real_

  signal <- if (is.na(latest)) "insufficient data"
    else if (latest > 80) "overbought"
    else if (latest < 20) "oversold"
    else "neutral"

  interpretation <- sprintf(
    "Current %d-period MFI is %.1f (%s). Positive money flow ratio %.2f.",
    window, latest, signal,
    tail(mfr[is.finite(mfr)], 1)
  )

  list(
    n = n,
    window = as.integer(window),
    mfi = mfi,
    latest = latest,
    signal = signal,
    interpretation = interpretation
  )
}
