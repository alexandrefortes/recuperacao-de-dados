function main(splash, args)
  -- Configurações iniciais
  splash:set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
  splash.js_enabled = true
  splash.indexeddb_enabled = true
  assert(splash:go(args.url))
  splash:set_viewport_full()

  -- Espera inicial para o carregamento da página
  assert(splash:wait(10))
  
  -- Scroll para o final da página para carregar conteúdo dinâmico
  splash:evaljs("window.scrollTo(0, document.body.scrollHeight);")
  assert(splash:wait(3))  -- Espera adicional após o scroll
  
  -- Verifica se o elemento necessário foi carregado
  local ready = splash:evaljs("document.querySelector('.container h2') !== null")
  if not ready then
    return { error = "Elemento necessário não encontrado." }
  end
  
  -- Retorna os resultados
  return {
    html = splash:html(),
    png = splash:png(),
    har = splash:har(),
  }
end
