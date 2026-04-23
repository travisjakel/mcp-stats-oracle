#' Terminal-rendered ggplot2 visualizations via plotcli::ggplotcli
#'
#' Returns ASCII-art plots Claude can read directly — no image I/O. Three modes:
#' `line` (time series), `histogram` (distribution), `scatter` (bivariate).
#' Output is the plot as a single string of newlined ASCII.
#'
#' @param plot_type one of "line", "histogram", "scatter"
#' @param data numeric vector (required for line/histogram; y for scatter if `x` given)
#' @param x numeric vector (required for scatter)
#' @param y numeric vector (required for scatter)
#' @param title optional title string
#' @param bins integer, number of histogram bins (default 30)
#' @param width,height integer canvas size in terminal cells (default 70x16)
#' @return list(plot_type, plot, n, interpretation)

run_plot <- function(plot_type = "line",
                     data = NULL,
                     x = NULL, y = NULL,
                     title = "",
                     bins = 30L,
                     width = 70L,
                     height = 16L) {
  if (!requireNamespace("plotcli", quietly = TRUE) ||
      !requireNamespace("ggplot2", quietly = TRUE)) {
    return(list(error = "plotcli and ggplot2 required"))
  }
  suppressPackageStartupMessages({
    library(plotcli)
    library(ggplot2)
  })

  width  <- max(40L, min(120L, as.integer(width)))
  height <- max(10L, min(40L,  as.integer(height)))

  make_line <- function(v) {
    v <- as.numeric(v); v <- v[is.finite(v)]
    if (length(v) < 2) stop("line plot needs at least 2 finite points")
    df <- data.frame(x = seq_along(v), y = v)
    p <- ggplot(df, aes(x, y)) + geom_line() + xlab("index") + ylab("value")
    if (nzchar(title)) p <- p + ggtitle(title)
    list(
      plot = p,
      interpretation = sprintf(
        "Line plot of %d points. Range [%.3f, %.3f]; last value %.3f.",
        length(v), min(v), max(v), tail(v, 1)
      )
    )
  }

  make_histogram <- function(v, bins) {
    v <- as.numeric(v); v <- v[is.finite(v)]
    if (length(v) < 5) stop("histogram needs at least 5 finite points")
    bins <- max(5L, min(100L, as.integer(bins)))
    df <- data.frame(v = v)
    p <- ggplot(df, aes(v)) + geom_histogram(bins = bins) + xlab("value") + ylab("count")
    if (nzchar(title)) p <- p + ggtitle(title)
    list(
      plot = p,
      interpretation = sprintf(
        "Histogram of %d points (%d bins). Mean %.3f, sd %.3f.",
        length(v), bins, mean(v), stats::sd(v)
      )
    )
  }

  make_scatter <- function(x, y) {
    x <- as.numeric(x); y <- as.numeric(y)
    n <- min(length(x), length(y))
    x <- x[seq_len(n)]; y <- y[seq_len(n)]
    keep <- is.finite(x) & is.finite(y)
    x <- x[keep]; y <- y[keep]
    if (length(x) < 5) stop("scatter needs at least 5 complete (x,y) pairs")
    df <- data.frame(x = x, y = y)
    p <- ggplot(df, aes(x, y)) + geom_point() + xlab("x") + ylab("y")
    if (nzchar(title)) p <- p + ggtitle(title)
    rho <- suppressWarnings(stats::cor(x, y))
    list(
      plot = p,
      interpretation = sprintf(
        "Scatter of %d (x,y) pairs. Pearson correlation %.3f.",
        length(x), rho
      )
    )
  }

  built <- switch(plot_type,
    line       = make_line(data),
    histogram  = make_histogram(data, bins),
    scatter    = make_scatter(x, y),
    stop(sprintf("unknown plot_type '%s' (expected line|histogram|scatter)", plot_type))
  )

  lines <- capture.output(
    plotcli::ggplotcli(
      built$plot,
      width = width,
      height = height,
      canvas_type = "ascii",
      border = TRUE,
      grid = FALSE
    )
  )
  plot_text <- paste(lines, collapse = "\n")

  list(
    plot_type = plot_type,
    width = width,
    height = height,
    plot = plot_text,
    interpretation = built$interpretation
  )
}
