# LLM MAS Control

## Description

A lot of existing research on using LLMs for operators of multi-agent systems has focused on whether it is possible to control multi-agent systems (MAS) using LLMs ignoring the crucial question of **should** we use LLMs for MAS control.  This project is an exploration as a part of CS 7633 (HRI) to perform a user experiment with comparing a traditional Real-Time Strategy (RTS) style interface to a text-based LLM interface for a simple game using the Robotarium.

## Setup

I wrote a justfile (kind of like a Makefile, but the syntax is a little bit better) so if you have uv and just installed just run `just init`, which will build the protobufs and setup the common library.  To test a package you can also run `just test <package-name>`.  During development, the goal is to make sure all operations can be executed via the justfile.

## Dependencies

* [uv](https://docs.astral.sh/uv/getting-started/installation/)
* [just](https://github.com/casey/just)
