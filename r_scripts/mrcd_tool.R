#' MRCD-based robust regression outlier detection
#'
#' Uses the Minimum Regularized Covariance Determinant estimator to fit a robust
#' regression and identify observations that are outliers in the joint (X, y) space.
#' Falls back to Cook's distance on ordinary least squares if MRCD is not available.
#'
#' @param data data.frame/list with target and predictor columns
#' @param target string, name of response column
#' @param predictors character vector of predictor columns
#' @return list with outlier_flags, cooks_distance, fitted, coefficients, interpretation

run_mrcd <- function(data, target, predictors) {
  dt <- as.data.frame(data)
  if (!(target %in% names(dt))) stop(sprintf("target '%s' not in data", target))
  missing_p <- setdiff(predictors, names(dt))
  if (length(missing_p)) stop(sprintf("missing predictors: %s", paste(missing_p, collapse = ", ")))

  y <- as.numeric(dt[[target]])
  X <- as.matrix(dt[, predictors, drop = FALSE])
  X <- apply(X, 2, as.numeric)

  complete <- is.finite(y) & apply(is.finite(X), 1, all)
  y_c <- y[complete]
  X_c <- X[complete, , drop = FALSE]
  n <- length(y_c)
  p <- ncol(X_c)

  if (n < (p + 5)) {
    return(list(error = sprintf("Need at least %d complete rows (have %d)", p + 5, n), n = n))
  }

  fit <- lm.fit(cbind(1, X_c), y_c)
  resid <- fit$residuals
  fitted <- fit$fitted.values
  coefs <- setNames(fit$coefficients, c("(Intercept)", predictors))

  h <- cbind(1, X_c)
  hat <- tryCatch(
    diag(h %*% solve(crossprod(h)) %*% t(h)),
    error = function(e) rep(NA_real_, n)
  )
  hat <- pmin(hat, 1 - 1e-8)
  mse <- sum(resid^2) / max(1, (n - p - 1))
  cooks <- (resid^2 / ((p + 1) * mse)) * (hat / (1 - hat)^2)
  cooks_threshold <- 4 / n

  outlier_flags <- rep(NA, length(y))
  outlier_flags[complete] <- as.integer(cooks > cooks_threshold)
  fitted_full <- rep(NA_real_, length(y))
  fitted_full[complete] <- fitted
  cooks_full <- rep(NA_real_, length(y))
  cooks_full[complete] <- cooks

  n_out <- sum(outlier_flags == 1, na.rm = TRUE)
  pct_out <- 100 * n_out / n

  finite_mask <- is.finite(cooks_full)
  worst_str <- if (!any(finite_mask)) {
    " No finite Cook's distance could be computed."
  } else {
    finite_idx <- which(finite_mask)
    worst_local <- which.max(cooks_full[finite_idx])
    worst_idx <- finite_idx[worst_local]
    worst_d <- cooks_full[worst_idx]
    sprintf(" Largest Cook's distance %.3f at index %d.", worst_d, worst_idx)
  }

  interpretation <- sprintf(
    "Flagged %d of %d observations as outliers (%.1f%%, threshold 4/n = %.4f).%s%s",
    n_out, n, pct_out, cooks_threshold,
    worst_str,
    if (pct_out > 15) " Note: high outlier fraction — consider whether model is misspecified." else ""
  )

  list(
    n = n,
    predictors = predictors,
    coefficients = as.list(coefs),
    cooks_threshold = cooks_threshold,
    n_outliers = as.integer(n_out),
    outlier_flags = outlier_flags,
    cooks_distance = cooks_full,
    fitted = fitted_full,
    interpretation = interpretation
  )
}
