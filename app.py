with tab1:
    fig_s = go.Figure()
    fig_s.add_trace(
        go.Scatter(
            x=df_curva_base["Hora"],
            y=df_curva_base["Almacenamiento_Ideal_Pct"],
            mode="lines",
            name="Curva Meta Almacenamiento (%)",
            line=dict(color="#2980b9", width=2, dash="dash", shape="spline"),
        )
    )

    if not df_dia_actual.empty:
        fig_s.add_trace(
            go.Scatter(
                x=df_dia_ord["Hora_Int"],
                y=df_dia_ord["Almacenamiento_Bosque_Pct"],
                mode="lines+markers",
                name="Almacenamiento Real (Transcurrido)",
                line=dict(color="#27ae60", width=3, shape="spline"),
                marker=dict(size=8),
            )
        )

        ultima_h = df_dia_ord["Hora_Int"].max()
        if ultima_h < 23:
            horas_p = list(range(int(ultima_h), 24))
            ultimo_a = float(
                df_dia_ord[df_dia_ord["Hora_Int"] == ultima_h][
                    "Almacenamiento_Bosque_Pct"
                ].values[0]
            )
            # AQUÍ ESTABA EL PEQUEÑO DETALLE QUE FALTABA CONECTAR:
            proy_a = np.linspace(ultimo_a, meta_amanecer_pct, len(horas_p))
            fig_s.add_trace(
                go.Scatter(
                    x=horas_p,
                    y=proy_a,
                    mode="lines",
                    name="Proyección Resto del Día",
                    line=dict(
                        color="#e67e22", width=3, dash="dot", shape="spline"
                    ),
                )
            )
