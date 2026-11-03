"""Shablonlar geometriyasi (ichki koordinatalar, pt, y yuqoriga; sahifa: x*k, ty - y*k)."""
CARTON = {
    "cefoperazone": dict(k=0.99802, ty=529.236623,
                         xs=(28.26298, 56.612068, 155.824091, 255.036113, 354.248136, 453.460159),
                         y0=172.327759, y1=356.579218, lid=455.79124, tongue=484.140328,
                         legend=(0, 0, 250, 168), keep_legend=False, knee=(300, 450)),
    "ampicillin": dict(k=0.998335, ty=515.813613,
                       xs=(28.351888, 56.699864, 155.91191, 255.11613, 354.32035, 453.548046),
                       y0=174.373445, y1=344.453474, lid=443.665519, tongue=472.013495,
                       legend=None, keep_legend=True, knee=(300, 440)),
}

LABEL = {
    # labels: (x0, y0, x1, y1) haqiqiy o'lcham va kattalashtirilgan nusxa; cx: dizayn qismi (nisbiy)
    "cefoperazone": dict(k=1.0, ty=403.99982,
                         labels=[(186.082024, 274.378787, 412.855512, 359.417869),
                                 (29.253864, 62.167803, 412.855512, 206.019397)],
                         cx=(0.359, 0.654), legend=(20, 255, 182, 335)),
    "ampicillin": dict(k=0.998992, ty=400.285972,
                       labels=[(193.879056, 275.943075, 363.956773, 355.312155),
                               (28.743822, 61.316539, 363.956773, 217.747685)],
                       cx=(0.349, 0.651), legend=None),
}


def page_rect(g, x0, y0, x1, y1):
    k, ty = g["k"], g["ty"]
    return (k * x0, ty - k * y1, k * x1, ty - k * y0)
