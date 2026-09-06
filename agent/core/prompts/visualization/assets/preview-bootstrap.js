// Executed after pinned libraries and before generated fragment scripts.
if (window.Chart) {
  Chart.defaults.color = '#b9c0cf';
  Chart.defaults.borderColor = '#303745';
  Chart.defaults.font.family = 'system-ui, sans-serif';
  Chart.defaults.animation = false;
}
if (window.mermaid) {
  mermaid.initialize({startOnLoad:false, securityLevel:'strict', theme:'base',
    themeVariables:{darkMode:true, background:'#0f1115', primaryColor:'#1c212b',
      primaryTextColor:'#f7f3ea', primaryBorderColor:'#f4c95d', lineColor:'#b9c0cf',
      secondaryColor:'#11141a', tertiaryColor:'#171a21', fontFamily:'system-ui, sans-serif'}});
}
