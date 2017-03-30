# -*- coding: utf-8 -*-

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.web.client import Agent, readBody
from txsocksx.http import SOCKS5Agent

def get_tor_agent(socks_host='127.0.0.1', socks_port=9050):
    '''An HTTP agent that uses SOCKS5 to proxy all requests through the socks_port

    It is implicitly understood that the socks_port points to the locally configured 
    tor daemon'''
    torServerEndpoint = TCP4ClientEndpoint(reactor, socks_host, socks_port)
    agent = SOCKS5Agent(reactor, proxyEndpoint=torServerEndpoint)
    return agent


def get_web_agent():
    '''An HTTP agent that connects to the web without using tor'''
    return Agent(reactor, connectTimeout=4)


def get_page(agent, url):
    request = agent.request('GET', url)

    def cbResponse(response):
        return readBody(response)

    request.addCallback(cbResponse)

    return request
