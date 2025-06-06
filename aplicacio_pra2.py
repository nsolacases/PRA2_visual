from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
import os
import shutil

carpeta = 'assets'
origen_imatge = 'dataset.jpg'
desti_imatge = os.path.join(carpeta, 'dataset.jpg')

if not os.path.exists(carpeta):
    os.makedirs(carpeta)
    print(f'Carpeta "{carpeta}" creada.')

if not os.path.exists(desti_imatge):
    shutil.copy(origen_imatge, desti_imatge)
    print(f'Imatge copiada a {desti_imatge}')
else:
    print(f'Imatge ja existia a {desti_imatge}')


df = pd.read_csv("dades_amb_benestar.csv")

# Netegem les columnes que seran usades
for col in ["Industry", "Job_Role", "Mental_Health_Condition", "Work_Location", "Access_to_Mental_Health_Resources", "Company_Support_for_Remote_Work", "Satisfaction_with_Remote_Work"]:
    df[col] = df[col].astype(str).str.strip().str.replace('\n', '').str.replace('\r', '')

# === Sankey ===
counts = df.groupby(["Job_Role", "Work_Location"]).size().reset_index(name='Count')
all_labels = list(pd.unique(counts["Job_Role"].tolist() + counts["Work_Location"].tolist()))
label_map = {label: i for i, label in enumerate(all_labels)}
fig_sankey = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_labels
    ),
    link=dict(
        source=[label_map[job] for job in counts["Job_Role"]],
        target=[label_map[wl] for wl in counts["Work_Location"]],
        value=counts["Count"]
    ))])

fig_sankey.update_layout(title_text="Distribució dels diferents rols de feina segons Modalitat de Treball", font_size=10)

# === Sunburst ===
fig_sunburst = px.sunburst(
    df,
    path=["Industry", "Job_Role", "Mental_Health_Condition", "Access_to_Mental_Health_Resources", "Work_Location"],
    color="Work_Location",
    color_discrete_map={
        "Hybrid": "#ffb347",
        "Remote": "#3ebf93",
        "Onsite": "#4a9eda"
    },
    title="Distribució per Indústria, Rol, Condició Mental, Accés a Recursos i Modalitat Treball."
)

fig_sunburst.update_layout(
    title_font_size=22,
    title_x=0.5,
    margin=dict(t=50, l=0, r=0, b=0),
    paper_bgcolor="#f7f7f7",
    plot_bgcolor="#f7f7f7"
)

# === Mapa ===

counts = df.groupby(['Region', 'Mental_Health_Condition']).size().reset_index(name='Count')
total_per_region = counts.groupby('Region')['Count'].transform('sum')
counts['Percent'] = counts['Count'] / total_per_region * 100

continent_coords = {
    'Europe': {'lat': 54.5, 'lon': 15.3},
    'Asia': {'lat': 34.0, 'lon': 100.0},
    'North America': {'lat': 54.5, 'lon': -105.0},
    'South America': {'lat': -10.0, 'lon': -55.0},
    'Africa': {'lat': 1.5, 'lon': 17.3},
    'Oceania': {'lat': -25.0, 'lon': 133.0}
}
counts['lat'] = counts['Region'].map(lambda x: continent_coords.get(x, {'lat': None})['lat'])
counts['lon'] = counts['Region'].map(lambda x: continent_coords.get(x, {'lon': None})['lon'])

data_dict = {cond: counts[counts['Mental_Health_Condition'] == cond] for cond in counts['Mental_Health_Condition'].unique()}

# == Boxplot ==

df['Experience_Group'] = pd.cut(
    df['Years_of_Experience'],
    bins=[0, 5, 10, 15, 20, 25, 30, 40],
    labels=['0-5', '6-10', '11-15', '16-20', '21-25', '26-30', '31+']
)
experience_order = ['0-5', '6-10', '11-15', '16-20', '21-25', '26-30', '31+']
df['Experience_Group'] = pd.Categorical(df['Experience_Group'], categories=experience_order, ordered=True)
fig_experience = px.box(
    df,
    x='Experience_Group',
    y='Wellbeing_Index',
    color='Experience_Group',
    title="Distribució del Benestar segons Franges d'Experiència",
    labels={'Experience_Group': 'Franges d\'experiència', 'Wellbeing_Index': 'Índex de Benestar'}
)
fig_experience.update_layout(showlegend=False)

# == bar plot

support_resource_counts = df.groupby(['Company_Support_for_Remote_Work', 'Access_to_Mental_Health_Resources']).size().reset_index(name='count')

fig_support = px.bar(
    support_resource_counts,
    x='Company_Support_for_Remote_Work',
    y='count',
    color='Access_to_Mental_Health_Resources',
    barmode='group',
    title="Relació entre el Suport de l'Empresa i l'Accés a Recursos de Salut Mental",
    labels={
        'Company_Support_for_Remote_Work': "Suport de l'empresa al teletreball",
        'count': 'Nombre de persones',
        'Access_to_Mental_Health_Resources': 'Accés a recursos de salut mental'
    }
)

# ==== violin plot
fig_violin = px.violin(
    df,
    x='Work_Location',
    y='Productivity_Change',
    box=True,
    points="all",
    color='Work_Location',
    title="Distribució de la Productivitat segons la Modalitat de Treball",
    labels={
        'Work_Location': 'Modalitat de Treball',
        'Productivity_Change': 'Canvi de Productivitat'
    }
)



# App
app = Dash(__name__)

app.layout = html.Div([
    html.H2("Mapa Interactiu: Salut Mental per Regió", style={'textAlign': 'center'}),
    html.Label("Selecciona una condició de salut mental:"),
    dcc.Dropdown(
        id='condicio-dropdown',
        options=[{'label': c, 'value': c} for c in data_dict.keys()],
        value=list(data_dict.keys())[0]
    ),
    dcc.Graph(id='mapa-interactiu')
])

@app.callback(
    Output('mapa-interactiu', 'figure'),
    Input('condicio-dropdown', 'value'),
)
def update_map(condicio_sel):
    df_filtrat = data_dict[condicio_sel]
    fig = px.scatter_geo(df_filtrat,
                         lat='lat', lon='lon',
                         size='Percent',
                         color='Percent',
                         color_continuous_scale='Reds',
                         size_max=40,
                         scope='world',
                         title=f'Percentatge de {condicio_sel} per regió',
                         hover_name='Region',
                         labels={'Percent': '% persones'})
    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
    return fig

# == Layout de  l'aplicació ===
app.layout = html.Div([
    html.H1("Impacte del Teletreball en la Salut Mental i el Benestar", style={'textAlign': 'center'}),
    dcc.Tabs([

        # PESTANYA 1 - Introducció
        dcc.Tab(label='Introducció', children=[
            html.Div([
                html.H3("Context:"),
                html.P([
                    "Disposem d'un dataset que conté dades per estudiar com afecta la modalitat de treball ",
                    "(remot, híbrid o presencial) a la salut mental i el benestar dels empleats."
                ]),

                html.H3("Característiques:"),
                html.P("Dataset de 5.000 registres i 23 columnes."),

                html.P([
                    "Variables quantitatives: Variables com Age, Hours_worked_per_week, ",
                    "Work_life_Balance_Rating, Stress_Level, Mental_Health_Condition, ",
                    "Social_Isolation_Rating, Productivity_Change, Physical_Activity, Sleep_Quantity."
                ]),

                html.P([
                    " Variables qualitatives (categòriques): Employee_ID, Gender, Work_Location, ",
                    "Job_Role, Industry, Mental_Health_Condition, Region, Access_to_mental_health_resources, ",
                    "Satisfaction_with_Remote_Work, Company_support_for_remote_work."
                ]),

                html.H3("Objectius"),
                html.P([
                    "Analitzar com afecta la modalitat de treball (remot, híbrid o presencial) ",
                    "a la salut mental, el benestar i la productivitat de les persones ",
                    "treballadores mitjançant l'exploració visual d'un conjunt de dades real."
                ]),

                html.Ul([
                    html.Li("1. Identificar patrons de salut mental segons la modalitat de treball."),
                    html.Li("2. Explorar diferències per edat, experiència i ubicació geogràfica."),
                    html.Li("3. Relacionar el perfil laboral amb el benestar emocional."),
                    html.Li("4. Analitzar si el rol, la indústria o el suport de l'empresa influeixen en la salut mental."),
                    html.Li("5. Visualitzar la relació entre productivitat percebuda i condicions laborals."),
                    html.Li("6. Oferir una eina interactiva per entendre millor les dades.")
                ]),

                html.Img(src="/assets/dataset.jpg", style={"width": "60%"})
            ], style={'padding': '20px'})
        ]),

        # PESTANYA 2 - Rol i Salut
        dcc.Tab(label='Rol i modalitat', children=[
            html.Div([
                html.H2("Rol i modalitat de treball", style={'textAlign': 'center'}),
                html.P("""
                    Aquest gràfic ens permet veure per les diferents distribucions dels job roles del dataset 
                    el nombre de persones que realitzen cada modalitat de treball.
                """, style={'fontSize': '16px', 'lineHeight': '1.6'}),
                dcc.Graph(figure=fig_sankey)
            ], style={'padding': '30px'})
        ]),

        # PESTANYA 3 - Mapa per Regió
        dcc.Tab(label='Mapa per Regió', children=[
            html.Div([
                html.H2("Distribució geogràfica de la salut mental", style={'textAlign': 'center'}),
                html.P("""
                    Aquest mapa mostra quin percentatge de cada condició de salut mental apareix a cada regió del món, 
                    segons el dataset. Es poden identificar patrons regionals i diferències culturals o estructurals 
                    que poden influir en la salut mental de les persones treballadores.
                """, style={'fontSize': '16px', 'lineHeight': '1.6'}),

                html.Label("Selecciona una condició de salut mental:", style={'marginTop': '20px'}),
                dcc.Dropdown(
                    id='condicio-dropdown',
                    options=[{'label': c, 'value': c} for c in data_dict.keys()],
                    value=list(data_dict.keys())[0]
                ),

                dcc.Graph(id='mapa-interactiu')
            ], style={'padding': '30px'})
        ]),

        # PESTANYA 4 - Perfil Laboral i Salut
        dcc.Tab(label='Perfil Laboral i Salut', children=[
            html.Div([
                html.H2("Perfil laboral i condicions de salut mental", style={'textAlign': 'center'}),
                html.P("""
                    Aquest gràfic mostra la relació jeràrquica entre la indústria, el rol laboral, 
                    les condicions de salut mental, l'accés a recursos i la modalitat de treball.
                    És útil per entendre com el context laboral pot influir en el benestar emocional
                    de les persones treballadores.
                """, style={'fontSize': '16px', 'lineHeight': '1.6'}),
                dcc.Graph(figure=fig_sunburst)
            ], style={'padding': '30px'})
        ]),

        # PESTANYA 6 - Suport i Salut Mental
        dcc.Tab(label='Suport i Salut Mental', children=[
            html.Div([
                html.H2("Suport de l'Empresa i Salut Mental", style={'textAlign': 'center'}),
                html.P("Aquest gràfic mostra la relació entre el nivell de suport de l’empresa al teletreball i les condicions de salut mental dels treballadors."),
                dcc.Graph(figure=fig_support)
            ], style={'padding': '30px'})
        ]),


        # PESTANYA 7 - Conclusions
        dcc.Tab(label='Conclusions', children=[
            html.Div([
                html.H3("Conclusions"),
                html.P("Resum dels principals resultats i recomanacions."),
                html.P("""A través d’aquesta anàlisi, he pogut explorar com diferents factors laborals 
                      poden influir en la salut mental i el benestar de les persones."""),

                html.P("Limitacions: la baixa variabilitat en algunes variables i el desequilibri de categories han dificultat la representació clara de certs gràfics."),

                html.H2("Benestar segons l'Experiència Laboral", style={'textAlign': 'center'}),
                html.P("Aquest gràfic mostra la distribució del benestar emocional segons les franges d'anys d'experiència."),
                dcc.Graph(figure=fig_experience),

                html.H2("Relació entre Productivitat i el model de treball", style={'textAlign': 'center'}),
                html.P("Aquest gràfic com varia la productivitat segons la modalitat de treball."),
                dcc.Graph(figure=fig_violin),
            ], style={'padding': '30px'})
        ]),

    ])
]) 

if __name__ == '__main__':
    app.run_server(debug=True)
