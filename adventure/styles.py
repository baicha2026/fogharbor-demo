CSS = """
<style>
[data-testid="stAppViewContainer"] { background:#131c23; }
[data-testid="stSidebar"] { background:#1a252d; border-right:1px solid #35414a; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p { color:#ece2ce; }
[data-testid="stHeader"] {background:transparent;}
[data-testid="stHeader"] button {color:#abb5b7;}
[data-testid="stIconMaterial"] {color:#abb5b7;}
.block-container {padding:1.8rem 2.8rem 2.5rem; max-width:1660px;}
[data-testid="stToolbar"] {opacity:.4;}
h1,h2,h3,p,label,[data-testid="stMarkdownContainer"] {color:#ece2ce;}
[data-testid="stCaptionContainer"] {color:#abb5b7;}
[data-testid="stMetricValue"] {color:#e6c786; font-size:1.55rem;}
[data-testid="stMetricLabel"] {color:#a9b6b8;}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:#35414a!important;
 background:#1a252d; border-radius:10px!important;}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
 border-radius:6px; border:1px solid #43535b; color:#ece2ce; background:#26353b;
 min-height:2.65rem; font-weight:500;}
[data-testid="stButton"] button[kind="primary"] {background:#b18a48; border-color:#dcbd7c;
 color:#101b23;}
[data-testid="stButton"] button:disabled {opacity:.35;}
[data-testid="stButton"] button:hover {border-color:#e3c380; color:#efd49a;}
[data-testid="stExpander"] {border-color:#35414a; background:#1a252d;}
[data-testid="stProgress"] [role="progressbar"] {background:#35434a;}
.game-mast {display:flex; justify-content:space-between; align-items:center;
 border-bottom:1px solid #36434b; padding-bottom:16px; margin-bottom:22px;}
.game-brand {font-family:Georgia,serif; font-size:25px; color:#e9cd94;}
.game-tag {font-size:10px; letter-spacing:2px; color:#7e9ba0;}
.game-title {font-size:27px; color:#f1dfb9; margin:0 0 5px; font-weight:650;}
.game-section {font-size:10px; letter-spacing:2px; color:#7e9ba0; margin-bottom:8px;}
.game-intro {color:#a9b8b8; font-size:13px; line-height:1.8; margin-bottom:25px;}
.quest-card {border-left:3px solid #c4a268; padding:4px 0 4px 14px; margin:14px 0;}
.quest-card strong {color:#efdaaa; font-size:16px;}
.quest-card p {font-size:13px; color:#acbab9; margin:7px 0;}
.speaker {font-size:11px; color:#e9c581; letter-spacing:1px; margin-bottom:8px;}
.game-footer {border-top:1px solid #35414a; padding-top:14px; margin-top:24px;
 color:#8aa0a4; font-size:11px;}
[data-testid="stImage"] img {image-rendering:pixelated; border-radius:5px;}
@media(max-width:850px){
 .block-container{padding:1.2rem .9rem;} .game-tag{display:none;}
 .st-key-story_direction_buttons [data-testid="stHorizontalBlock"] {flex-wrap:nowrap; gap:8px;}
 .st-key-story_direction_buttons [data-testid="stColumn"] {
  min-width:0!important; width:auto!important; flex:1 1 0!important;}
}
</style>
"""
