#' TSrepr feature-clipping compression
#'
#' Compresses a hourly/cyclical window (e.g. 24 hourly observations) into 8
#' shape features: max_1, sum_1, max_0, cross, f_0, l_0, f_1, l_1.
#' Uses TSrepr::repr_feaclip when available; otherwise reproduces the
#' feature-clipping logic in base R.
#'
#' @param data numeric vector (default expected length 24)
#' @return list with features + interpretation

run_tsrepr <- function(data) {
  x <- as.numeric(data)
  x <- x[is.finite(x)]
  if (length(x) < 4) {
    return(list(error = "Need at least 4 finite points", n = length(x)))
  }

  if (requireNamespace("TSrepr", quietly = TRUE)) {
    feats <- tryCatch(TSrepr::repr_feaclip(x), error = function(e) NULL)
  } else {
    feats <- NULL
  }

  if (is.null(feats)) {
    m <- mean(x)
    b <- as.integer(x > m)
    rle_b <- rle(b)
    ones_runs <- rle_b$lengths[rle_b$values == 1]
    zero_runs <- rle_b$lengths[rle_b$values == 0]
    feats <- c(
      max_1 = if (length(ones_runs)) max(ones_runs) else 0,
      sum_1 = sum(b),
      max_0 = if (length(zero_runs)) max(zero_runs) else 0,
      cross = sum(diff(b) != 0),
      f_0 = if (any(b == 0)) which(b == 0)[1] else length(b),
      l_0 = if (any(b == 0)) tail(which(b == 0), 1) else 0,
      f_1 = if (any(b == 1)) which(b == 1)[1] else length(b),
      l_1 = if (any(b == 1)) tail(which(b == 1), 1) else 0
    )
  }

  feats <- as.list(feats)
  names(feats) <- sub("\\.$", "", names(feats))

  interpretation <- sprintf(
    "Longest above-mean run: %d; longest below-mean run: %d; %d mean-crossings. Pattern is %s.",
    feats$max_1, feats$max_0, feats$cross,
    if (feats$cross < 2) "monotone/flat"
    else if (feats$max_1 > feats$max_0 * 2) "above-mean dominant"
    else if (feats$max_0 > feats$max_1 * 2) "below-mean dominant"
    else "balanced oscillation"
  )

  list(n = length(x), features = feats, interpretation = interpretation)
}
